import os

from flask import Flask, render_template, redirect, request, jsonify, flash

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route('/desafio200k')
def desafio200k():
    return render_template('desafio200k.html')

@app.route('/autenticar', methods=['POST'])
def autenticar():
    email = request.form.get('email')
    cpf = request.form.get('cpf')
    categoria = request.form.get('categoria')
    
    # Here you would typically:
    # 1. Validate the input data
    # 2. Generate and send verification code to email
    # 3. Store the verification code and user data temporarily
    
    return render_template('authentic200k.html')

@app.route('/verificar-codigo', methods=['POST'])
def verificar_codigo():
    codigo = request.form.get('codigo')
    
    # Here you would typically:
    # 1. Verify the code against stored code
    # 2. Process the registration if valid
    # 3. Redirect to success or error page
    
    return redirect('/success')  # Or appropriate response



port = int(os.environ.get("PORT", 5000))
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=port, debug=True)

