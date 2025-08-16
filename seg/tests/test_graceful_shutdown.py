#!/usr/bin/env python3
"""
Test script for graceful shutdown of ThreeJsRenderer threads
"""
import sys
import os
import time
import signal

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from seg.threejs_viewer import ThreeJsRenderer

def main():
    print("Starting ThreeJsRenderer...")
    renderer = ThreeJsRenderer()
    
    # Start the servers
    renderer.render(port=8080)
    
    print("Servers started. Waiting 3 seconds before shutdown...")
    time.sleep(3)
    
    print("Initiating graceful shutdown...")
    renderer.shutdown()
    
    print("Test completed successfully!")

if __name__ == "__main__":
    main()
