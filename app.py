from flask import Flask, render_template, redirect, request, make_response, jsonify, flash, session
from flask_mail import Mail, Message
from flask_mysqldb import MySQL
from dotenv import load_dotenv
import pdfkit
import os
import re
import random
import json

load_dotenv()  # Carrega as variáveis do arquivo .env

app = Flask(__name__)
app.secret_key = 'EM1QW765QNNDK9'

# Configuração do Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Substitua pelo seu servidor SMTP
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = 'ecmsistemasdeveloper@gmail.com'
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False

mail = Mail(app)

# Configuração MySQL
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB')

mysql = MySQL(app)


# Global variables for the receipt
receipt_data = {
    'titulo': 'Comprovante de Inscrição',
    'data': '14/01/2025',
    'evento': '4º DESAFIO 200K PORTO VELHO-HUMAITÁ - 2025',
    'endereco': 'AV. Jorge Teixeira, Espaço Alternativo - Porto Velho/RO',
    'dataevento': '04, 05 e 06/07/2025',
    'participante': 'ELIENAI CARVALHO MOMTEIRO',
    'km': 'Quarteto - 50 km',
    'valor': 'R$ 500,00',
    'inscricao': '123455456456',    
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

@app.route('/cadastro_atleta')
def cadastro_atleta():
    return render_template('cadastro_atleta.html')

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

@app.route('/login')
def login():
    return render_template('login.html')

def validar_cpf(cpf):
    # Remove caracteres não numéricos
    cpf = ''.join(re.findall(r'\d', str(cpf)))
    
    # Verifica se o CPF tem 11 dígitos
    if len(cpf) != 11:
        return False
    
    # Verifica se todos os dígitos são iguais (ex: 111.111.111-11)
    if cpf == cpf[0] * 11:
        return False
    
    # Calcula o primeiro dígito verificador
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    primeiro_dv = 11 - (soma % 11)
    primeiro_dv = 0 if primeiro_dv >= 10 else primeiro_dv
    
    # Calcula o segundo dígito verificador
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    segundo_dv = 11 - (soma % 11)
    segundo_dv = 0 if segundo_dv >= 10 else segundo_dv
    
    # Verifica se os dígitos verificadores estão corretos
    return cpf[-2:] == f"{primeiro_dv}{segundo_dv}"


@app.route('/validar-cpf', methods=['GET'])
def validar_cpf_route():
    
    cpf = request.args.get('cpf', '')
    # Remove caracteres não numéricos
    cpf = ''.join(filter(str.isdigit, cpf))
    is_valid = validar_cpf(cpf)

    return jsonify({'valid': is_valid})

@app.route('/verificar-cpf', methods=['GET'])
def verificar_cpf_existente():
    cpf = request.args.get('cpf', '')
    # Remove caracteres não numéricos
    cpf = ''.join(filter(str.isdigit, cpf))
    
    try:
        cur = mysql.connection.cursor()
        cur.execute('SELECT IDATLETA FROM ecmrun.ATLETA_TT WHERE CPF = %s', (cpf,))
        result = cur.fetchone()
        cur.close()
        
        return jsonify({'exists': bool(result)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


#### ADD 14/01/2025 13H ####################################


@app.route('/generate-pdf', methods=['POST'])
def generate_pdf():
    # Renderiza o template HTML
    html = render_template('comprovante_insc.html', data=request.form)
    
    # Gera o PDF a partir do HTML
    pdf = pdfkit.from_string(html, False)  # False retorna o PDF como bytes
    
    # Cria uma resposta para download do PDF
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=comprovante.pdf'
    
    return response

@app.route('/send-email', methods=['POST'])
def send_email():
    #pdf = pdfkit.from_string(render_template('comprovante_insc.html', data=request.form), False)
    
    msg = Message("Comprovante PDF", recipients=["naicm12@gmail.com"])
    #msg.attach("comprovante001.pdf", "application/pdf", pdf)
    
    mail.send(msg)
    
    return "Email enviado com sucesso!"


@app.route('/send-email-link')
def send_email_link():
    # Chama a função send_email() diretamente
    return send_email()


@app.route('/send-email2', methods=['POST'])
def send_email2():
    # Renderiza o template HTML com os dados do recibo
    html_content = render_template('comprovante_insc.html', **receipt_data)

    # Criação da mensagem de e-mail
    msg = Message(subject='Comprovante PDF',
                  sender='ecmsistemasdeveloper@gmail.com',
                  recipients=['naicm12@gmail.com'])

    # Define o corpo do e-mail como HTML
    msg.html = html_content

    # Envia o e-mail
    mail.send(msg)
    return "Email enviado com sucesso!"

###################

@app.route('/pesquisarCEP', methods=['GET'])
def pesquisar_cep():
    try:
        cep = request.args.get('cep', '').strip()
        
        # Remove caracteres não numéricos do CEP
        cep = ''.join(filter(str.isdigit, cep))
        
        if not cep or len(cep) != 8:
            return jsonify({'error': 'CEP inválido'}), 400
            
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT id_logradouro, CEP, descricao, UF, complemento, 
                   descricao_sem_numero, descricao_cidade, descricao_bairro 
            FROM ecmrun.logradouro
            WHERE CEP = %s
        """, (cep,))
        
        result = cur.fetchone()
        cur.close()
        
        if result:
            return jsonify({
                'success': True,
                'data': {
                    'id_logradouro': result[0],
                    'cep': result[1],
                    'descricao': result[2],
                    'uf': result[3],
                    'complemento': result[4],
                    'descricao_sem_numero': result[5],
                    'descricao_cidade': result[6],
                    'descricao_bairro': result[7]
                }
            })
        else:
            return jsonify({'success': False, 'message': 'CEP não encontrado'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)