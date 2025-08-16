from flask import Flask, render_template

app = Flask(__name__, static_url_path="/static")
app.config.from_object(__name__)

@app.route("/" , methods=["GET"])
def index():
    return "<p>Hello, World!</p>"
   
@app.route("/cad/<file_stem>", methods=["GET"])
def file(file_stem):
    return render_template('cad.html')
