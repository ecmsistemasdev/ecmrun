import os
import random
import json
from flask import Flask, render_template, redirect, request, jsonify, flash, session

app = Flask(__name__)
app.secret_key = 'EM1QW765QNNDK9'

# Global variables for the receipt
receipt_data = {
    'titulo': 'Comprovante de Inscrição',
    'data': '14/01/2025',
    'endereco': 'AV. Jorge Teixeira, Espaço Alternativo - Porto Velho/RO',
    'inscricao': '123455456456',
    'km': '200',
    'valor': 'R$ 500,00',
    'participante': 'ELIENAI CARVALHO MOMTEIRO DA SILVA MONTEIRO',
    'nome': '4º DESAFIO 200K PORTO VELHO-HUMAITÁ - 2025',
    'obs': 'Observações importantes sobre o evento vão aqui.'
}

@app.route("/")
def index():
    return render_template("index.html")

@app.route('/comprovante')
def comprovante():
    return render_template('comprovante_insc.html', **receipt_data)

@app.route('/desafio200k')
def desafio200k():
    return render_template('desafio200k.html')

@app.route('/autenticar', methods=['POST'])
def autenticar():
    email = request.form.get('email')
    cpf = request.form.get('cpf')
    categoria = request.form.get('categoria')

    verification_code = str(random.randint(1000, 9999))
    session['verification_code'] = verification_code
    
    return render_template('autenticar200k.html', verification_code=verification_code)

@app.route('/verificar-codigo', methods=['POST'])
def verificar_codigo():
    codigo = request.form.get('codigo')
    stored_code = session.get('verification_code')
    
    if codigo == stored_code:
        session.pop('verification_code', None)
        return redirect('/success')
    else:
        return redirect('/autenticar')

@app.route('/estados')
def estados():
    with open('static/json/estados.json', encoding='utf-8') as f:
        data = json.load(f)
    return jsonify(data)

@app.route('/municipios')
def municipios():
    with open('static/json/municipios.json', encoding='utf-8') as f:
        data = json.load(f)
    return jsonify(data)

@app.route('/inscricao200k')
def inscricao200k():
    return render_template('inscricao200k.html')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)