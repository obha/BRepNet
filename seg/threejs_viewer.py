import asyncio
import atexit
import http
from http.server import BaseHTTPRequestHandler, HTTPServer, SimpleHTTPRequestHandler
import json
import os
from pathlib import Path
import re
import signal
import socket
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
import uuid
import websockets

from OCC.Core.Tesselator import ShapeTesselator
from OCC import VERSION as OCC_VERSION

from seg.dom import NXDOM

class Event():
    def __init__(self, client):
        self.client = client
        
    def send(self, data):
        payload = json.dumps(payload)
        self.client.send(payload)
    
    def receive(self, data):
        return None
    
class ThreeLoadShape(Event):
    def __init__(self, client):
        super().__init__(client)
     
class ThreeShapeClick(Event):
    def __init__(self, client):
        super().__init__(client)

class WebSocketBridge():
    def __init__(self):
        self.clients = {}
        self.events = []
        self.shutdown_event = threading.Event()
        self.server = None
        self.loop = None
    
    def get(self, etype) -> Event:
        if len(self.clients) == 0:
            return None
        
        client = list(self.clients)[0]
        events = self.clients[client]
        return events.get(etype.__name__)
        
    def add_event(self, event):
        self.events.append( event )
        
    def _get_client_events(self, client):
        events = {}
        
        for e in self.events:
            events[e.__name__] = e(client)
            
        if client.id not in self.clients:
            self.clients[client] = events
        
        return self.clients[client]

    
    async def handle_client(self, websocket, path):
        events = self._get_client_events(websocket)
        
        try:
            async for message in websocket:
                data = json.loads(message)
                eid = data.get('eid')
                if eid in events:
                    e:Event = events.get(eid, None)
                    if e is None:
                        raise ValueError('Event is not executable')
                    
                    result = e.receive(data)
                    if result is not None:
                        await websocket.send(json.dumps({'eid':eid, 'data':result}))
                
        except Exception as e:
            await websocket.send(json.dumps({
                'type': 'error',
                'message': str(e)
            }))
        finally:
            del self.clients[websocket]

               
    def start(self, port=8765):
        def start_websocket():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            print(f"Starting WebSocket server on ws://localhost:{port}")
            self.server = websockets.serve(self.handle_client, "localhost", port)
            self.loop.run_until_complete(self.server)
            
            # Run until shutdown is requested
            try:
                self.loop.run_forever()
            except Exception as e:
                print(f"WebSocket server error: {e}")
            finally:
                self.loop.close()
                print("WebSocket server stopped")
            
        thread = threading.Thread(target=start_websocket, daemon=False, name="Bridge-Thread")
        thread.start()
        return thread
    
    def stop(self):
        """Gracefully stop the WebSocket server"""
            
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
    
class ThreeJsRenderer():
    """
    A 3D shape renderer using Three.js that runs HTTP and WebSocket servers.
    
    This class now supports graceful shutdown of all background threads:
    - WebSocket server thread for real-time communication
    - HTTP server thread for serving static content and API endpoints
    
    Shutdown is triggered by:
    - SIGINT (Ctrl+C) or SIGTERM signals
    - Calling shutdown() method explicitly
    - Program exit (via atexit handler)
    """
    def __init__(self):
        self._path = tempfile.mkdtemp()
        
        self.bridge = WebSocketBridge()
        self.bridge.add_event(ThreeShapeClick)
        self.bridge.add_event(ThreeLoadShape)
        
        
        self._3js_shapes = {}
        self.http_server = None
        self.http_thread = None
        self.shutdown_event = threading.Event()
        self._shutdown_called = False
        
        self.init()

    def init(self):
        statics_path = os.path.join(os.getcwd(), "seg", "static")
        subprocess.run(["cp", "-r", statics_path, self._path])

    def DisplayShape(self, shape, export_edges=False, color=(0.65, 0.65, 0.7), specular_color=(0.2, 0.2, 0.2), shininess=0.9, transparency=0., line_color=(0, 0., 0.), line_width=1., mesh_quality=1.):

        shape_uuid = uuid.uuid4()
        shape_hash = "shp%s" % shape_uuid.hex
        tess = ShapeTesselator(shape)
        tess.Compute(compute_edges=False,
                     mesh_quality=1,
                     parallel=True)
        
        # shape_full_path = os.path.join(self._path, shape_hash + '.json')
        self._3js_shapes[shape_hash] = [export_edges, color, specular_color, shininess, transparency, line_color, line_width]


        shape_json = tess.ExportShapeToThreejsJSONString(shape_uuid.hex)
        headers = {'Content-type': 'application/json'}
        try:
            conn = http.client.HTTPConnection("localhost:8080")
            conn.request("POST", "/d-shape", shape_json.encode(), headers)
        except Exception as e:
            print("Error sending shape data:", e)
        finally:
            conn.close()

        
    def _http_server(self, port=8080):
        dir = self._path
        bridge = self.bridge
        
        class RouterRequestHandler(BaseHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                
        
            def do_POST(self):
                path = self.path.split('?')[0] 
                content_len = int(self.headers.get('Content-Length'))
                body = json.loads(self.rfile.read(content_len))
                
                if path.startswith('/d-shape'):
                    bridge.get(ThreeLoadShape).send(body)
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    return 

            def do_GET(self):
                path = self.path.split('?')[0]  # Remove query params
                
                if path.startswith("/cad/"):
                    self._render(self.serve_cad_page(path[5:]))
                # Route: Static files (CSS, JS, images)
                elif path.startswith('/static/'):
                    self.serve_static_file(path)
                # Route: Not found
                else:
                   self._render( self.serve_404() )
                
            def serve_static_file(self, path):
                file_path = Path(f"{dir}/{path}")

                with open(file_path, 'r') as f:
                    content = f.read()
                    
                    self.send_response(200)

                    if file_path.suffix == '.js':
                        self.send_header('Content-type', 'text/javascript')
                    elif file_path.suffix == '.css':
                        self.send_header('Content-type', 'text/css')
                    elif file_path.suffix in ['.gif','.jpeg', '.png', '.tiff', '.svg']:
                        self.send_header('Content-type', f"image/{file_path.suffix[1:]}")
                    elif file_path.suffix in ['.mpeg','.mp4', '.quicktime', '.webm']:
                        self.send_header('Content-type', f"video/{file_path.suffix[1:]}")
                    self.send_header('Cache-Control', 'max-age=3600')
                    self.end_headers()
                    self.wfile.write(content.encode())
                    return 
                         
            def serve_404(self):
                dom = NXDOM("html", lang="en")
                head = dom.append(dom.root, "head")
                dom.append(head, "link", rel="stylesheet", href="/static/css/global.css")
                dom.append(head, "script", src="https://rawcdn.githack.com/mrdoob/three.js/r126/build/three.min.js")
                dom.append(head, "script", src="https://rawcdn.githack.com/mrdoob/three.js/r126/examples/js/controls/TrackballControls.js")
                dom.append(head, "script", src="https://rawcdn.githack.com/mrdoob/three.js/r126/examples/js/libs/stats.min.js")
                dom.append(head, "script", src="/static/js/main.js", type="module")
                dom.append(head, "meta", charset="utf-8")
                dom.append(head, "title", text="NetworkX DOM")
                body = dom.append(dom.root, "body")
                dom.append(body, "h1", text="404 Not Found")
                
                return dom
                    
            def serve_cad_page(self, id):
                dom = NXDOM("html", lang="en")
                head = dom.append(dom.root, "head")
                dom.append(head, "link", rel="stylesheet", href="/static/css/global.css")
                dom.append(head, "script", src="https://rawcdn.githack.com/mrdoob/three.js/r126/build/three.min.js")
                dom.append(head, "script", src="https://rawcdn.githack.com/mrdoob/three.js/r126/examples/js/controls/TrackballControls.js")
                dom.append(head, "script", src="https://rawcdn.githack.com/mrdoob/three.js/r126/examples/js/libs/stats.min.js")
                dom.append(head, "script", src="/static/js/main.js", type="module")
                dom.append(head, "meta", charset="utf-8")
                dom.append(head, "title", text="NetworkX DOM")
                dom.append(dom.root, "body")
                
                return dom

            def _render(self, dom, headers={}):
                self.send_response(200)

                self.send_header('Content-type', 'text/html')
                self.send_header('Cache-Control', 'no-cache')
                self.end_headers()
                self.wfile.write(dom.to_html().encode())
                return 
            
        class ThreadingSimpleServer(socketserver.ThreadingMixIn, HTTPServer):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.allow_reuse_address = True
                
            def shutdown_request(self, request):
                """Override to handle shutdown gracefully"""
                try:
                    request.shutdown(socket.SHUT_WR)
                except OSError:
                    pass  # Some clients may have already closed
                self.close_request(request)
        
        print(f"Starting Http server on http://localhost:{port}")
        self.http_server = ThreadingSimpleServer(('0.0.0.0', port), RouterRequestHandler)
        
        # Run server until shutdown is requested
        try:
            self.http_server.serve_forever()
        except Exception as e:
            print(f"HTTP server error: {e}")
        finally:
            self.http_server.server_close()
            print("HTTP server stopped")
            
    def render(self, port=8080):
        self.websocket_thread = self.bridge.start()
        self.http_thread = threading.Thread(target=self._http_server, args=(port,), daemon=False, name="HTTP-Server-Thread")
        self.http_thread.start()
    
    def shutdown(self):
        """Gracefully shutdown all threads and servers"""
        if self._shutdown_called:
            return
        
        self._shutdown_called = True
        print("Shutting down servers...")
        
        # Stop WebSocket server
        self.bridge.stop()
        
        # Stop HTTP server
        if self.http_server:
            self.http_server.shutdown()
        
        # Wait for threads to finish
        if self.websocket_thread and self.websocket_thread.is_alive():
            self.websocket_thread.join(timeout=5)
            
        if self.http_thread and self.http_thread.is_alive():
            self.http_thread.join(timeout=5)
        
        print("All servers stopped")

        

if __name__ == "__main__":
    from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox
    
    renderer = ThreeJsRenderer()
    box = BRepPrimAPI_MakeBox(100., 200., 300.).Shape()

    atexit.register(renderer.shutdown)
    
    renderer.render()

    
    renderer.DisplayShape(box)
    

    def _signal_handler(signum, frame):
        """Handle shutdown signals"""
        print(f"\nReceived signal {signum}, shutting down gracefully...")
        renderer.shutdown()
        sys.exit(0)
        
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)
        

