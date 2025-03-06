from flask import Flask, render_template, redirect, request, make_response, jsonify, flash, session
from flask_mail import Mail, Message
from flask_cors import CORS
from flask_mysqldb import MySQL
from dotenv import load_dotenv
from datetime import datetime
from pytz import timezone
import mercadopago
import requests
import hashlib
import pdfkit
import os
import re
import random
import json
import uuid
import logging

load_dotenv()  # Carrega as variáveis do arquivo .env

app = Flask(_name_)
logging.basicConfig(level=logging.DEBUG)

sdk = mercadopago.SDK(os.getenv('MP_ACCESS_TOKEN'))

app.secret_key = os.getenv('SECRET_KEY')
CORS(app)

# Configuração do Flask-Mail
app.config['MAIL_SERVER'] = os.getenv('SMTP_SERVER')  # Substitua pelo seu servidor SMTP
app.config['MAIL_PORT'] = os.getenv('SMTP_PORT') 
app.config['MAIL_USERNAME'] = os.getenv('EMAIL_USER') 
app.config['MAIL_PASSWORD'] = os.getenv('EMAIL_PASSWORD') 
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_MAX_EMAILS'] = None
app.config['MAIL_TIMEOUT'] = 10  # segundos
app.config['MP_ACCESS_TOKEN'] = os.getenv('MP_ACCESS_TOKEN')

mail = Mail(app)

# Configuração MySQL
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB')

mysql = MySQL(app)

#sdk = mercadopago.SDK(os.getenv('MP_ACCESS_TOKEN2'))

# Global variables for the receipt
receipt_data = {
    'titulo': 'Comprovante de Inscrição',
    'data': '14/01/2025',
    'evento': '4º DESAFIO 200K PORTO VELHO-HUMAITÁ - 2025',
    'endereco': 'AV. Jorge Teixeira, Espaço Alternativo - Porto Velho/RO',
    'dataevento': '04, 05 e 06/07/2025',
    'participante': 'ELIENAI CARVALHO MOMTEIRO',
    'km': 'Solo - 200 km',
    'valor': 'R$ 500,00',
    'inscricao': '123455456456',    
    'obs': 'Observações importantes sobre o evento vão aqui.'
}

var_email = ""

def fn_email(valor):
    global var_email
    var_email = valor

@app.route("/")
def index():
    return render_template("index.html")

@app.route('/backyard2025/resultado')
def backyard2025_resultado():
    # Obter parâmetros de filtro
    sexo_filter = request.args.get('sexo', '')
    tipo_corrida_filter = request.args.get('tipo_corrida', '')
    
    # Iniciar a consulta base
    query = """
        SELECT idatleta, concat(lpad(cast(nrpeito as char(3)),3,0),' - ', nome) as atleta, 
        sexo, tipo_corrida, 
        case when nr_voltas>0 then nr_voltas else 'DNF' end as nvoltas,
        case when nr_voltas>0 then cast((nr_voltas * 6706) as char) else 'DNF' end as km
        FROM 2025_atletas
        WHERE 1=1
    """
    
    # Adicionar filtros se fornecidos
    if sexo_filter:
        query += f" AND sexo = '{sexo_filter}'"
    if tipo_corrida_filter:
        query += f" AND tipo_corrida = '{tipo_corrida_filter}'"
    
    # Ordenação
    query += " ORDER BY nr_voltas DESC, nome"
    
    # Executar a consulta
    cursor = mysql.connection.cursor()
    cursor.execute(query)
    atletas = cursor.fetchall()
    
    # Obter listas únicas para os filtros de dropdown
    cursor.execute("SELECT DISTINCT sexo FROM 2025_atletas ORDER BY sexo")
    sexos = [row[0] for row in cursor.fetchall()]
    
    cursor.execute("SELECT DISTINCT tipo_corrida FROM 2025_atletas ORDER BY tipo_corrida")
    tipos_corrida = [row[0] for row in cursor.fetchall()]
    
    cursor.close()
    
    return render_template(
        'backyard2025resultado.html', 
        atletas=atletas, 
        sexos=sexos, 
        tipos_corrida=tipos_corrida,
        sexo_filter=sexo_filter,
        tipo_corrida_filter=tipo_corrida_filter
    )


@app.route('/listar-estados', methods=['GET'])
def listar_estados():
    try:
        cursor = mysql.connection.cursor()
        
        cursor.execute("""
            SELECT uf, nome 
            FROM estado 
            ORDER BY nome
        """)
        
        estados_tuplas = cursor.fetchall()
        
        estados = []
        for estado in estados_tuplas:
            estados.append({
                'uf': estado[0],
                'nome': estado[1]
            })
            
        cursor.close()
        
        return jsonify({
            'success': True,
            'estados': estados
        })
    except Exception as e:
        app.logger.error(f"Erro ao buscar estados: {e}")
        return jsonify({
            'success': False,
            'mensagem': 'Erro ao buscar estados'
        }), 500

@app.route('/listar-cidades', methods=['GET'])
def listar_cidades():
    try:
        uf = request.args.get('uf')
        
        if not uf:
            return jsonify({
                'success': False,
                'mensagem': 'UF não fornecida'
            }), 400
        
        cursor = mysql.connection.cursor()
        
        cursor.execute("""
            SELECT c.id_cidade, c.descricao
            FROM cidade c
            JOIN estado e ON c.uf = e.uf
            WHERE e.uf = %s
            ORDER BY c.descricao
        """, (uf,))
        
        cidades_tuplas = cursor.fetchall()  # Armazene os resultados primeiro
        
        cidades = []
        for cidade in cidades_tuplas:
            cidades.append({
                'id_cidade': cidade[0],
                'descricao': cidade[1]
            })
            
        cursor.close()  # Feche o cursor depois de processar os resultados

        return jsonify({
            'success': True,
            'cidades': cidades
        })
    except Exception as e:
        app.logger.error(f"Erro ao buscar cidades para UF {uf}: {e}")
        return jsonify({
            'success': False,
            'mensagem': f'Erro ao buscar cidades para UF {uf}'
        }), 500

# Funções auxiliares do backyard
def calculate_seconds_difference(start_time_str, end_time_str):
    start_time = datetime.strptime(start_time_str, '%d/%m/%Y %H:%M:%S')
    end_time = datetime.strptime(end_time_str, '%d/%m/%Y %H:%M:%S')
    return (end_time - start_time).total_seconds()

def format_time_difference(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

# Rotas do backyard
@app.route('/backyard/lancamento')
def backyard_lancamento():
    return render_template('backyardlancamento.html')

@app.route('/backyard/pesquisar_atleta/<nrpeito>')
def pesquisar_atleta(nrpeito):
    try:
        cur = mysql.connection.cursor()

        query = """
            SELECT la.id, la.idlargada, a.idatleta, a.nome, a.nrpeito,
                la.largada, a.tipo_corrida, la.nulargada, la.parcial, la.chegada,
                CONCAT(LPAD(CAST(a.nrpeito AS CHAR(3)),3,'0'),' - ', a.nome) as atleta
            FROM bm_largadas_atletas la, bm_atletas a
            WHERE (la.chegada = '' OR la.chegada IS NULL)
                AND la.idlargada = (
                    SELECT MAX(idlargada) 
                    FROM bm_largadas_atletas
                    WHERE (chegada = '' OR chegada IS NULL)
                    AND idatleta = a.idatleta
                )
                AND la.idatleta = a.idatleta
                AND a.nrpeito = %s
        """
        
        cur.execute(query, (nrpeito,))
        result = cur.fetchone()
        
        if result:
            columns = [desc[0] for desc in cur.description]
            result_dict = dict(zip(columns, result))
            
            return jsonify({
                'success': True,
                'atleta': result_dict['atleta'],
                'data': result_dict
            })
        else:
            cur.execute("SELECT * FROM bm_atletas WHERE nrpeito = %s", (nrpeito,))
            atleta_exists = cur.fetchone()
            
            return jsonify({
                'success': False,
                'message': 'Atleta não encontrado'
            })
            
    except Exception as e:
        print(f"Erro na consulta: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        })
    finally:
        cur.close()

@app.route('/backyard/lancar_chegada', methods=['POST'])
def lancar_chegada():
    try:
        #data = request.get_json()
        #nrpeito = data['nrpeito']
        #chegada = data['chegada']
        
        data = request.get_json()
        nrpeito = data['nrpeito']
        chegada = data['chegada'].replace(', ', ' ')  # Remove a vírgula e mantém apenas um espaço


        cur = mysql.connection.cursor()
        
        # Buscar dados do atleta
        cur.execute("""
            SELECT la.*, a.tipo_corrida 
            FROM bm_largadas_atletas la, bm_atletas a
            WHERE la.idatleta = a.idatleta
            AND a.nrpeito = %s
            AND (la.chegada = '' OR la.chegada IS NULL)
        """, (nrpeito,))
        
        result = cur.fetchone()
        if not result:
            return jsonify({
                'success': False,
                'error': 'Atleta não encontrado'
            })
            
        columns = [desc[0] for desc in cur.description]
        atleta = dict(zip(columns, result))
        
        # Próxima ordem de chegada
        cur.execute("""
            SELECT COALESCE(MAX(ordem_chegada),0) as ID 
            FROM bm_largadas_atletas 
            WHERE idlargada = %s
        """, (atleta['idlargada'],))
        
        result = cur.fetchone()
        ordem_chegada = (result[0] or 0) + 1
        
        # Cálculo de tempo e status
        segundos = calculate_seconds_difference(atleta['largada'], chegada)
        tempo_chegada = format_time_difference(segundos)
        
        vstatus = 'D' if segundos > 3599 else 'A'
        
        if atleta['idlargada'] == 3 and atleta['tipo_corrida'] == 'Três voltas':
            vstatus = 'D'
            
        # Atualizar registro
        cur.execute("""
            UPDATE bm_largadas_atletas
            SET 
                chegada = %s,
                tempochegada = %s,
                ordem_chegada = %s,
                usuario_chegada = %s
            WHERE id = %s
        """, (chegada, tempo_chegada, ordem_chegada, 'ADM', atleta['id']))
        
        mysql.connection.commit()
        
        return jsonify({
            'success': True,
            'message': 'Chegada lançada com sucesso'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })
    finally:
        cur.close()

# Rota para renderizar a página eventos.html
@app.route('/eventos')
def eventos():
    return render_template('eventos.html')

# Get all eventos
@app.route('/api/eventos')
def get_eventos():
    cur = mysql.connection.cursor()
    cur.execute("SELECT IDEVENTO, DESCRICAO FROM EVENTO ORDER BY DTINICIO DESC")
    eventos = [{'IDEVENTO': row[0], 'DESCRICAO': row[1]} for row in cur.fetchall()]
    cur.close()
    return jsonify(eventos)

# Get specific evento
@app.route('/api/eventos/<int:evento_id>')
def get_evento(evento_id):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT IDEVENTO, DESCRICAO, DTINICIO, DTFIM, HRINICIO, 
               INICIO_INSCRICAO, FIM_INSCRICAO, 
               INICIO_INSCRICAO_EXT, FIM_INSCRICAO_EXT 
        FROM EVENTO WHERE IDEVENTO = %s
    """, (evento_id,))
    row = cur.fetchone()
    cur.close()
    
    if row:
        evento = {
            'IDEVENTO': row[0],
            'DESCRICAO': row[1],
            'DTINICIO': row[2], # .strftime('%d/%m/%Y') if row[2] else '',
            'DTFIM': row[3], #.strftime('%d/%m/%Y') if row[3] else '',
            'HRINICIO': row[4], #.strftime('%H:%M') if row[4] else '',
            'INICIO_INSCRICAO': row[5], #.strftime('%d/%m/%Y %H:%M:%S') if row[5] else '',
            'FIM_INSCRICAO': row[6], #.strftime('%d/%m/%Y %H:%M:%S') if row[6] else '',
            'INICIO_INSCRICAO_EXT': row[7], #.strftime('%d/%m/%Y %H:%M:%S') if row[7] else '',
            'FIM_INSCRICAO_EXT': row[8] #.strftime('%d/%m/%Y %H:%M:%S') if row[8] else ''
        }
        return jsonify(evento)
    return jsonify(None)

# Update evento
@app.route('/api/eventos', methods=['PUT'])
def update_evento():
    data = request.json
    
    # Converter as datas do formato brasileiro para o formato do MySQL
    dtinicio = data['DTINICIO'] #datetime.strptime(data['DTINICIO'], '%d/%m/%Y').strftime('%Y-%m-%d')
    dtfim = data['DTFIM'] #datetime.strptime(data['DTFIM'], '%d/%m/%Y').strftime('%Y-%m-%d')
    hrinicio = data['HRINICIO']
    inicio_inscricao = data['INICIO_INSCRICAO'] #datetime.strptime(data['INICIO_INSCRICAO'], '%d/%m/%Y %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
    fim_inscricao = data['FIM_INSCRICAO'] #datetime.strptime(data['FIM_INSCRICAO'], '%d/%m/%Y %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
    inicio_inscricao_ext = data['INICIO_INSCRICAO_EXT'] #datetime.strptime(data['INICIO_INSCRICAO_EXT'], '%d/%m/%Y %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
    fim_inscricao_ext = data['FIM_INSCRICAO_EXT'] #datetime.strptime(data['FIM_INSCRICAO_EXT'], '%d/%m/%Y %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
    
    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE EVENTO 
        SET DESCRICAO = %s, 
            DTINICIO = %s,
            DTFIM = %s,
            HRINICIO = %s,
            INICIO_INSCRICAO = %s,
            FIM_INSCRICAO = %s,
            INICIO_INSCRICAO_EXT = %s,
            FIM_INSCRICAO_EXT = %s
        WHERE IDEVENTO = %s
    """, (
        data['DESCRICAO'], dtinicio, dtfim, hrinicio,
        inicio_inscricao, fim_inscricao,
        inicio_inscricao_ext, fim_inscricao_ext,
        data['IDEVENTO']
    ))
    mysql.connection.commit()
    cur.close()
    return jsonify({'message': 'Evento atualizado com sucesso'})

# Get modalidades for evento
@app.route('/api/modalidades/<int:evento_id>')
def get_modalidades(evento_id):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT IDITEM, DESCRICAO, 
               FORMAT(VLINSCRICAO, 2) as VLINSCRICAO, 
               FORMAT(VLTAXA, 2) as VLTAXA 
        FROM EVENTO_MODALIDADE 
        WHERE IDEVENTO = %s
    """, (evento_id,))
    modalidades = [
        {
            'IDITEM': row[0],
            'DESCRICAO': row[1],
            'VLINSCRICAO': row[2],
            'VLTAXA': row[3]
        } for row in cur.fetchall()
    ]
    cur.close()
    return jsonify(modalidades)

# Get specific modalidade
@app.route('/api/modalidade/<int:iditem>')
def get_modalidade(iditem):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT IDITEM, DESCRICAO, 
               FORMAT(VLINSCRICAO, 2) as VLINSCRICAO, 
               FORMAT(VLTAXA, 2) as VLTAXA 
        FROM EVENTO_MODALIDADE 
        WHERE IDITEM = %s
    """, (iditem,))
    row = cur.fetchone()
    cur.close()
    
    if row:
        modalidade = {
            'IDITEM': row[0],
            'DESCRICAO': row[1],
            'VLINSCRICAO': row[2],
            'VLTAXA': row[3]
        }
        return jsonify(modalidade)
    return jsonify(None)

# Update modalidade
@app.route('/api/modalidade', methods=['PUT'])
def update_modalidade():
    data = request.json
    
    # Converter valores monetários (remove R$ e vírgulas)
    vlinscricao = float(data['VLINSCRICAO'].replace('R$', '').replace('.', '').replace(',', '.').strip())
    vltaxa = float(data['VLTAXA'].replace('R$', '').replace('.', '').replace(',', '.').strip())
    
    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE EVENTO_MODALIDADE 
        SET DESCRICAO = %s,
            VLINSCRICAO = %s,
            VLTAXA = %s
        WHERE IDITEM = %s
    """, (data['DESCRICAO'], vlinscricao, vltaxa, data['IDITEM']))
    mysql.connection.commit()
    cur.close()
    return jsonify({'message': 'Modalidade atualizada com sucesso'})

@app.route("/checkout")
def checkout():

    # Get values from session
    vlinscricao = session.get('valoratual', 0)
    vltaxa = session.get('valortaxa', 0)
    valor_total = float(vlinscricao) + float(vltaxa)
    
    return render_template('checkout.html', 
                         valor_inscricao=vlinscricao,
                         valor_taxa=vltaxa,
                         valor_total=valor_total)


@app.route('/process_payment', methods=['POST'])
def process_payment():
    try:
        # Configurar log detalhado
        app.logger.setLevel(logging.INFO)
        
        # Receber dados do pagamento
        payment_data = request.json
        app.logger.info("Dados completos recebidos:")
        app.logger.info(json.dumps(payment_data, indent=2))
        
        device_id = payment_data.get('device_id')
        app.logger.info(f"Device ID recebido: {device_id}")

        if not device_id:
            app.logger.error("Device ID está ausente ou vazio")
            return jsonify({"error": "Device ID é obrigatório"}), 400
       
        
        # Validação de campos obrigatórios
        required_fields = [
            'token', 
            'transaction_amount', 
            'installments', 
            'payment_method_id',
            'payer',
            'device_id'
        ]
        
        for field in required_fields:
            if field not in payment_data:
                app.logger.error(f"Campo obrigatório ausente: {field}")
                raise ValueError(f"Campo obrigatório ausente: {field}")
        
        # Extrair e validar dados importantes
        installments = int(payment_data.get('installments', 1))
        transaction_amount = round(float(payment_data['transaction_amount']), 2)
        
        # Extrair dados do participante
        valor_total = round(float(payment_data.get('valor_total', 0)), 2)
        valor_atual = round(float(payment_data.get('valor_atual', 0)), 2)
        valor_taxa = round(float(payment_data.get('valor_taxa', 0)), 2)
        
        # Dados adicionais do participante
        camisa = payment_data.get('camiseta')
        apoio = payment_data.get('apoio')
        equipe = payment_data.get('equipe')
        equipe200 = payment_data.get('nome_equipe')
        integrantes = payment_data.get('integrantes')
        
        # Preparar dados da sessão
        session['valorTotal'] = transaction_amount
        session['numeroParcelas'] = installments
        session['valorParcela'] = transaction_amount / installments if installments > 0 else transaction_amount
        session['valorTotalsemJuros'] = valor_total
        session['valorAtual'] = valor_atual
        session['valorTaxa'] = valor_taxa
        session['formaPagto'] = 'CARTÃO DE CRÉDITO'
        session['Camisa'] = camisa
        session['Equipe'] = equipe
        session['Apoio'] = apoio
        session['Equipe200'] = equipe200
        session['Integrantes'] = integrantes
        
        # Gerar referência externa única
        external_reference = str(uuid.uuid4())
        
        # Preparar dados do item
        item_details = {
            "id": "DESAFIO_200K_SOLO",
            "title": "Inscrição Desafio 200k",
            "description": "Inscrição para corrida de 200km",
            "category_id": "SPORTS_EVENT",
            "quantity": 1,
            "unit_price": valor_atual,
            "total_amount": transaction_amount
        }
        
        # Preparar preferência de pagamento
        preference_data = {
            "items": [item_details],
            "notification_url": "https://ecmrun.com.br/webhook",
            "external_reference": external_reference
        }
        
        try:
            preference_response = sdk.preference().create(preference_data)
            if "response" not in preference_response:
                app.logger.error("Erro ao criar preferência de pagamento")
                raise ValueError("Erro ao criar preferência de pagamento")
        except Exception as pref_error:
            app.logger.error(f"Erro na criação da preferência: {str(pref_error)}")
            raise
        
        # Preparar dados do pagamento
        payment_info = {
            "transaction_amount": transaction_amount,
            "token": payment_data['token'],
            "description": "Inscrição Desafio 200k - Categoria Solo",
            "statement_descriptor": "ECMRUN DESAFIO 200K",
            "installments": installments,
            "payment_method_id": payment_data['payment_method_id'],
            "device_id": payment_data.get('device_id'),
            "external_reference": external_reference,
            "notification_url": "https://ecmrun.com.br/webhook",
            "payer": {
                "email": payment_data['payer']['email'],
                "identification": {
                    "type": payment_data['payer']['identification']['type'],
                    "number": payment_data['payer']['identification']['number']
                },
                "first_name": payment_data['payer']['first_name'],
                "last_name": payment_data['payer']['last_name']
            },
            "additional_info": {
                "items": [item_details],
                "payer": {
                    "first_name": payment_data['payer']['first_name'],
                    "last_name": payment_data['payer']['last_name'],
                    "registration_date": datetime.now().isoformat()
                },
                "ip_address": request.remote_addr,
                "user_agent": str(request.user_agent)
            }
        }
        
        app.logger.info("Dados do pagamento para processamento:")
        app.logger.info(json.dumps(payment_info, indent=2))
        
        # Processar pagamento
        try:
            payment_response = sdk.payment().create(payment_info)
            
            app.logger.info("Resposta do pagamento:")
            app.logger.info(json.dumps(payment_response, indent=2))
            
            if "response" not in payment_response:
                error_msg = payment_response.get("message", "Erro desconhecido")
                app.logger.error(f"Erro no processamento do pagamento: {error_msg}")
                return jsonify({
                    "error": "Erro ao processar pagamento",
                    "details": error_msg
                }), 400
            
            payment_data = payment_response["response"]
            
            # Verificar status do pagamento
            if payment_data.get("status") == "approved":
                # Lógica adicional para pagamento aprovado
                try:
                    # Exemplo de chamada para lançar pagamento
                    verification_response = requests.get(
                        f'/lanca-pagamento-cartao/{payment_data["id"]}', 
                        headers={'Accept': 'application/json'}
                    )
                    
                    if verification_response.status_code != 200:
                        app.logger.warning(f"Erro na verificação do pagamento: {verification_response.text}")
                
                except Exception as verification_error:
                    app.logger.error(f"Erro na verificação do pagamento: {str(verification_error)}")
                
                return jsonify(payment_data), 200
            else:
                app.logger.warning(f"Pagamento não aprovado. Status: {payment_data.get('status')}")
                return jsonify({
                    "message": "Pagamento não aprovado",
                    "status": payment_data.get("status")
                }), 400
        
        except Exception as payment_error:
            app.logger.error(f"Erro no processamento do pagamento: {str(payment_error)}")
            return jsonify({
                "error": "Erro interno no processamento do pagamento",
                "details": str(payment_error)
            }), 500
    
    except ValueError as validation_error:
        app.logger.error(f"Erro de validação: {str(validation_error)}")
        return jsonify({"error": str(validation_error)}), 400
    
    except Exception as general_error:
        app.logger.error(f"Erro geral no processamento: {str(general_error)}")
        return jsonify({"error": "Erro interno no servidor"}), 500

# @app.route('/process_payment', methods=['POST'])
# def process_payment():
#     try:
#         app.logger.info("Dados recebidos:")
#         payment_data = request.json
#         app.logger.info(payment_data)
        
#         installments = payment_data.get('installments', 1)
#         transaction_amount = payment_data.get('transaction_amount', 0)
        
#         # Round to 2 decimal places to avoid floating point precision issues
#         valor_total = round(float(payment_data.get('valor_total', 0)), 2)
#         valor_atual = round(float(payment_data.get('valor_atual', 0)), 2)
#         valor_taxa = round(float(payment_data.get('valor_taxa', 0)), 2)
#         camisa = payment_data.get('camiseta')
#         apoio = payment_data.get('apoio')
#         equipe = payment_data.get('equipe')
#         equipe200 = payment_data.get('nome_equipe')
#         integrantes = payment_data.get('integrantes')

#         session['valorTotal'] = transaction_amount #valor_total
#         session['numeroParcelas'] = installments
#         session['valorParcela'] = transaction_amount / installments if installments > 0 else transaction_amount
#         session['valorTotalsemJuros'] = valor_total
#         session['valorAtual'] = valor_atual
#         session['valorTaxa'] = valor_taxa
#         session['formaPagto'] = 'CARTÃO DE CRÉDITO'
#         session['Camisa'] = camisa
#         session['Equipe'] = equipe
#         session['Apoio'] = apoio
#         session['Equipe200'] = equipe200
#         session['Integrantes'] = integrantes

#         # Validar dados recebidos
#         required_fields = [
#             'token', 
#             'transaction_amount', 
#             'installments', 
#             'payment_method_id',
#             'payer'
#         ]
        
#         for field in required_fields:
#             if field not in payment_data:
#                 raise ValueError(f"Campo obrigatório ausente: {field}")

#         # Gerar referência externa única
#         external_reference = str(uuid.uuid4())
        
#         # Criar preferência de pagamento
#         preference_data = {
#             "items": [{
#                 "title": payment_data.get('description', 'Produto'),
#                 "quantity": 1,
#                 "currency_id": "BRL",
#                 "unit_price": float(payment_data['transaction_amount']),
#                 "description": payment_data.get('description_item', 'Produto'),
#                 "category_id": "others"
#             }],
#             "notification_url": "https://ecmrun.com.br/webhook",
#             "external_reference": external_reference
#         }
        
#         # Criar preferência
#         preference_response = sdk.preference().create(preference_data)
        
#         if "response" not in preference_response:
#             raise ValueError("Erro ao criar preferência de pagamento")
            
#         # Preparar dados do pagamento
#         payment_info = {
#             "transaction_amount": float(payment_data['transaction_amount']),
#             "token": payment_data['token'],
#             "description": payment_data.get('description', 'Produto'),
#             "installments": installments,      #"installments": int(payment_data['installments']),
#             "payment_method_id": payment_data['payment_method_id'],
#             "external_reference": external_reference,
#             "notification_url": "https://ecmrun.com.br/webhook",
#             "payer": payment_data['payer']
#         }

#         app.logger.info("Dados do pagamento:")
#         app.logger.info(payment_info)
        
#         # Processar pagamento
#         payment_response = sdk.payment().create(payment_info)
        
#         app.logger.info("Resposta do pagamento:")
#         app.logger.info(payment_response)
        
#         if "response" not in payment_response:
#             return jsonify({
#                 "error": "Erro ao processar pagamento",
#                 "details": payment_response.get("message", "Erro desconhecido")
#             }), 400
            
#         return jsonify(payment_response["response"]), 200
        
#     except ValueError as e:
#         app.logger.error(f"Erro de validação: {str(e)}")
#         return jsonify({"error": str(e)}), 400
#     except Exception as e:
#         app.logger.error(f"Erro no processamento: {str(e)}")
#         return jsonify({"error": str(e)}), 400


def get_receipt_data(payment_id):
    """Função separada para buscar dados do comprovante"""
    try:
        cur = mysql.connection.cursor()
        cur.execute('''
            SELECT I.DTPAGAMENTO, E.DESCRICAO, E.LOCAL, 
                CONCAT(E.DTINICIO,' ',E.HRINICIO,' - ',E.DTFIM) as DTEVENTO,
                CONCAT(A.NOME,' ',A.SOBRENOME) as NOME_COMPLETO, 
                CONCAT(M.DISTANCIA,' / ',M.DESCRICAO) AS DISTANCIA,
                I.VALOR, I.VALOR_PGTO, I.FORMAPGTO, I.IDPAGAMENTO
            FROM ecmrun.INSCRICAO I
            JOIN ecmrun.ATLETA A ON A.IDATLETA = I.IDATLETA
            JOIN ecmrun.EVENTO E ON E.IDEVENTO = I.IDEVENTO
            JOIN ecmrun.EVENTO_MODALIDADE M ON M.IDITEM = I.IDITEM
            WHERE I.IDPAGAMENTO = %s
        ''', (payment_id,))
        
        data = cur.fetchone()
        cur.close()
        return data
    except Exception as e:
        app.logger.error(f"Erro ao buscar dados: {str(e)}")
        raise

def send_organizer_notification(receipt_data):
    try:
        msg = Message(
            f'Nova Inscrição - 4º Desafio 200k - ID {receipt_data["inscricao"]}',
            sender=('ECM Run', 'adm@ecmrun.com.br'),
            recipients=['kelioesteves@hotmail.com']
            #recipients=['ecmsistemasdeveloper@gmail.com']
        )
        
        # Render the organizer notification template with receipt data
        msg.html = render_template('organizer_email.html', **receipt_data)
        mail.send(msg)
        app.logger.info("Notificação enviada para o organizador")
        return True
        
    except Exception as e:
        app.logger.error(f"Erro ao enviar notificação para o organizador: {str(e)}")
        return False


@app.route('/comprovante/<int:payment_id>')
def comprovante(payment_id):
    try:
        
        app.logger.info(f"Payment ID: {payment_id}")
        
        cur = mysql.connection.cursor()
        # Execute a SQL com o payment_id
        cur.execute('''
            SELECT I.DTPAGAMENTO, E.DESCRICAO, E.LOCAL, 
                CONCAT(E.DTINICIO,' ',E.HRINICIO,' - ',E.DTFIM) as DTEVENTO,
                CONCAT(A.NOME,' ',A.SOBRENOME) as NOME_COMPLETO, 
                CONCAT(M.DISTANCIA,' / ',M.DESCRICAO) AS DISTANCIA,
                I.VALOR, I.VALOR_PGTO, I.FORMAPGTO, I.IDPAGAMENTO, I.FLMAIL, I.IDINSCRICAO
            FROM ecmrun.INSCRICAO I, ecmrun.ATLETA A, 
            ecmrun.EVENTO E, ecmrun.EVENTO_MODALIDADE M
            WHERE M.IDITEM = I.IDITEM
            AND E.IDEVENTO = I.IDEVENTO
            AND A.IDATLETA = I.IDATLETA
            AND I.IDPAGAMENTO = %s
        ''', (payment_id,))
        
        receipt_data = cur.fetchone()
        cur.close()

        if not receipt_data:
            app.logger.info("Dados não encontrados")
            return "Dados não encontrados", 404
        
        # Converter a data de string para datetime
        #data_pagamento = datetime.strptime(receipt_data[0], '%d/%m/%Y %H:%M')  # Formato correto

        # Estruturar os dados do comprovante
        receipt_data_dict = { 
            'data': receipt_data[0],  # Formatar data
            'evento': receipt_data[1],
            'endereco': receipt_data[2],
            'dataevento': receipt_data[3],
            'participante': receipt_data[4],
            'km': receipt_data[5],
            'valor': f'R$ {receipt_data[6]:,.2f}',  # Formatar valor
            'valortotal': f'R$ {receipt_data[7]:,.2f}',  # Formatar valor
            'formapgto': receipt_data[8],
            'inscricao': str(receipt_data[9]),
            'obs': 'Sua inscrição dá direito a: Número de peito, camiseta, viseira, sacolinha, e após concluir: medalha e troféu. Obs: Será apenas um troféu por equipe.'
        }
        
        app.logger.info("Dados da Inscrição:")
        app.logger.info(receipt_data)

        flmail = receipt_data[10]
        id_inscricao = receipt_data[11]
        app.logger.info(f' FLMAIL: { flmail }')
        app.logger.info(f' ID INSC: { id_inscricao }')


        if flmail == 'N':

            # Enviar email com os dados do comprovante
            send_email(receipt_data_dict)
        
            # Enviar notificação para o organizador
            send_organizer_notification(receipt_data_dict)

            cur1 = mysql.connection.cursor()
            cur1.execute('''
                UPDATE ecmrun.INSCRICAO SET FLMAIL = 'S'
                WHERE IDINSCRICAO = %s
            ''', (id_inscricao,))

            mysql.connection.commit()
            cur1.close()


        return render_template('comprovante_insc.html', **receipt_data_dict)

    except Exception as e:
        app.logger.error(f"Erro ao buscar dados do comprovante: {str(e)}")
        return "Erro ao buscar dados", 500

@app.route('/vercomprovante/<int:payment_id>')
def vercomprovante(payment_id):
    try:
        
        app.logger.info(f"Payment ID: {payment_id}")
        
        cur = mysql.connection.cursor()
        # Execute a SQL com o payment_id
        cur.execute('''
            SELECT I.DTPAGAMENTO, E.DESCRICAO, E.LOCAL, 
                CONCAT(E.DTINICIO,' ',E.HRINICIO,' - ',E.DTFIM) as DTEVENTO,
                CONCAT(A.NOME,' ',A.SOBRENOME) as NOME_COMPLETO, 
                CONCAT(M.DISTANCIA,' / ',M.DESCRICAO) AS DISTANCIA,
                I.VALOR, I.VALOR_PGTO, I.FORMAPGTO, I.IDPAGAMENTO, I.FLMAIL, I.IDINSCRICAO
            FROM ecmrun.INSCRICAO I, ecmrun.ATLETA A, 
            ecmrun.EVENTO E, ecmrun.EVENTO_MODALIDADE M
            WHERE M.IDITEM = I.IDITEM
            AND E.IDEVENTO = I.IDEVENTO
            AND A.IDATLETA = I.IDATLETA
            AND I.IDPAGAMENTO = %s
        ''', (payment_id,))
        
        receipt_data = cur.fetchone()
        cur.close()

        if not receipt_data:
            app.logger.info("Dados não encontrados")
            return "Dados não encontrados", 404
        
        # Converter a data de string para datetime
        #data_pagamento = datetime.strptime(receipt_data[0], '%d/%m/%Y %H:%M:%S')  # Formato correto

        flmail = receipt_data[10]
        id_inscricao = receipt_data[11]
        app.logger.info(f' FLMAIL: { flmail }')
        app.logger.info(f' ID INSC: { id_inscricao }')

        # Estruturar os dados do comprovante
        receipt_data_dict = { 
            'data': receipt_data[0],  # Formatar data
            'evento': receipt_data[1],
            'endereco': receipt_data[2],
            'dataevento': receipt_data[3],
            'participante': receipt_data[4],
            'km': receipt_data[5],
            'valor': f'R$ {receipt_data[6]:,.2f}',  # Formatar valor
            'valortotal': f'R$ {receipt_data[7]:,.2f}',  # Formatar valor
            'formapgto': receipt_data[8],
            'inscricao': str(receipt_data[9]),
            'obs': 'Sua inscrição dá direito a: Número de peito, camiseta, viseira, sacolinha, e após concluir: medalha e troféu. Obs: Será apenas um troféu por equipe.'
        }
        
        app.logger.info("Dados da Inscrição:")
        app.logger.info(receipt_data)

        return render_template('vercomprovante.html', **receipt_data_dict)

    except Exception as e:
        app.logger.error(f"Erro ao buscar dados do comprovante: {str(e)}")
        return "Erro ao buscar dados", 500

@app.route('/comprovanteemail/<int:payment_id>')
def comprovanteemail(payment_id):
    try:
        
        app.logger.info(f"Payment ID: {payment_id}")
        
        cur = mysql.connection.cursor()
        # Execute a SQL com o payment_id
        cur.execute('''
            SELECT I.DTPAGAMENTO, E.DESCRICAO, E.LOCAL, 
                CONCAT(E.DTINICIO,' ',E.HRINICIO,' - ',E.DTFIM) as DTEVENTO,
                CONCAT(A.NOME,' ',A.SOBRENOME) as NOME_COMPLETO, 
                CONCAT(M.DISTANCIA,' / ',M.DESCRICAO) AS DISTANCIA,
                I.VALOR, I.VALOR_PGTO, I.FORMAPGTO, I.IDPAGAMENTO
            FROM ecmrun.INSCRICAO I, ecmrun.ATLETA A, 
            ecmrun.EVENTO E, ecmrun.EVENTO_MODALIDADE M
            WHERE M.IDITEM = I.IDITEM
            AND E.IDEVENTO = I.IDEVENTO
            AND A.IDATLETA = I.IDATLETA
            AND I.IDPAGAMENTO = %s
        ''', (payment_id,))
        
        receipt_data = cur.fetchone()
        cur.close()

        if not receipt_data:
            app.logger.info("Dados não encontrados")
            return "Dados não encontrados", 404
        
        # Estruturar os dados do comprovante
        receipt_data_dict = { 
            'data': receipt_data[0],  # Formatar data
            'evento': receipt_data[1],
            'endereco': receipt_data[2],
            'dataevento': receipt_data[3],
            'participante': receipt_data[4],
            'km': receipt_data[5],
            'valor': f'R$ {receipt_data[6]:,.2f}',  # Formatar valor
            'valortotal': f'R$ {receipt_data[7]:,.2f}',  # Formatar valor
            'formapgto': receipt_data[8],
            'inscricao': str(receipt_data[9]),
            'obs': 'Sua inscrição dá direito a: Número de peito, camiseta, viseira, sacolinha, e após concluir: medalha e troféu. Obs: Será apenas um troféu por equipe.'
        }
        
        app.logger.info("Dados da Inscrição:")
        app.logger.error(receipt_data)

        return render_template('comprovante_email.html', **receipt_data_dict)

    except Exception as e:
        app.logger.error(f"Erro ao buscar dados do comprovante: {str(e)}")
        return "Erro ao buscar dados", 500



@app.route('/pagpix')
def pagpix():
    return render_template('pagpix.html')


@app.route('/get_evento_data')
def get_evento_data():
    try:
        cur = mysql.connection.cursor()
        cur.execute('''
            SELECT E.IDEVENTO, E.DESCRICAO, E.DTINICIO, E.DTFIM, E.HRINICIO,
                E.LOCAL, E.CIDADEUF, E.INICIO_INSCRICAO, E.FIM_INSCRICAO,
                M.IDITEM, M.DESCRICAO AS MODALIDADE, M.DISTANCIA, M.KM,
                M.VLINSCRICAO, M.VLMEIA, M.VLTAXA
            FROM ecmrun.EVENTO E, ecmrun.EVENTO_MODALIDADE M
            WHERE M.IDEVENTO = E.IDEVENTO
                AND E.IDEVENTO = 1
        ''')
        
        results = cur.fetchall()
        cur.close()
        
        if not results:
            return jsonify({'error': 'Evento não encontrado'}), 404
            
        # Estruturar os dados
        evento_data = {
            'idevento': results[0][0],
            'descricao': results[0][1],
            'dtinicio': results[0][2],
            'dtfim': results[0][3],
            'hrinicio': results[0][4],
            'local': results[0][5],
            'cidadeuf': results[0][6],
            'inicio_inscricao': results[0][7],
            'fim_inscricao': results[0][8],
            'iditem': results[0][9],
            'modalidades': results[0][10]
        }
        
        # Adicionar todas as modalidades
        for row in results:
            modalidade = {
                'iditem': row[9],
                'descricao': row[10],
                'distancia': row[11],
                'km': row[12],
                'vlinscricao': float(row[13]) if row[13] else 0,
                'vlmeia': float(row[14]) if row[14] else 0,
                'vltaxa': float(row[15]) if row[15] else 0
            }
            evento_data['modalidades'].append(modalidade)
            
        return jsonify(evento_data)
        
    except Exception as e:
        print(f"Erro ao buscar dados do evento: {str(e)}")
        return jsonify({'error': str(e)}), 500
    
@app.route('/cupom200k')
def cupom200k():
    try:
        cur = mysql.connection.cursor()
        cur.execute('''
            SELECT E.IDEVENTO, E.DESCRICAO, E.DTINICIO, E.DTFIM, E.HRINICIO,
                E.LOCAL, E.CIDADEUF, E.INICIO_INSCRICAO, E.FIM_INSCRICAO,
                M.IDITEM, M.DESCRICAO AS MODALIDADE, M.DISTANCIA, M.KM,
                M.VLINSCRICAO, M.VLMEIA, M.VLTAXA, E.INICIO_INSCRICAO_EXT, E.FIM_INSCRICAO_EXT
            FROM ecmrun.EVENTO E, ecmrun.EVENTO_MODALIDADE M
            WHERE M.IDEVENTO = E.IDEVENTO
                AND E.IDEVENTO = 1
        ''')
        
        results = cur.fetchall()
        cur.close()
        
        if not results:
            return render_template('desafio200k.html', titulo="Evento não encontrado", modalidades=[])
            
        evento_titulo = results[0][1]  # DESCRICAO do evento
        modalidades = [{'id': row[9], 'descricao': row[10]} for row in results]
        vl200 = f'R$ {results[0][13]:,.2f}'
        vl100 = f'R$ {results[1][13]:,.2f}' 
        vl50 = f'R$ {results[2][13]:,.2f}'
        vl25 = f'R$ {results[3][13]:,.2f}'
        inicioinsc = results[0][16]
        fiminsc = results[0][17]        
        return render_template('cupom200k.html', titulo=evento_titulo, modalidades=modalidades,
                               vlSolo=vl200, vlDupla=vl100, vlQuarteto=vl50, vlOcteto=vl25, 
                               inicio_insc=inicioinsc, fim_insc=fiminsc)
        
    except Exception as e:
        print(f"Erro ao carregar página: {str(e)}")
        return render_template('desafio200k.html', titulo="Erro ao carregar evento", modalidades=[])


@app.route('/desafio200k')
def desafio200k():
    try:
        cur = mysql.connection.cursor()
        cur.execute('''
            SELECT E.IDEVENTO, E.DESCRICAO, E.DTINICIO, E.DTFIM, E.HRINICIO,
                E.LOCAL, E.CIDADEUF, E.INICIO_INSCRICAO, E.FIM_INSCRICAO,
                M.IDITEM, M.DESCRICAO AS MODALIDADE, M.DISTANCIA, M.KM,
                M.VLINSCRICAO, M.VLMEIA, M.VLTAXA, E.INICIO_INSCRICAO_EXT, E.FIM_INSCRICAO_EXT
            FROM ecmrun.EVENTO E, ecmrun.EVENTO_MODALIDADE M
            WHERE M.IDEVENTO = E.IDEVENTO
                AND E.IDEVENTO = 1
        ''')
        
        results = cur.fetchall()
        cur.close()
        
        if not results:
            return render_template('desafio200k.html', titulo="Evento não encontrado", modalidades=[])
            
        evento_titulo = results[0][1]  # DESCRICAO do evento
        dt_incio = results[0][2]     
        modalidades = [{'id': row[9], 'descricao': row[10]} for row in results]
        vl200 = f'R$ {results[0][13]:,.2f}'
        vl100 = f'R$ {results[1][13]:,.2f}' 
        vl50 = f'R$ {results[2][13]:,.2f}'
        vl25 = f'R$ {results[3][13]:,.2f}'
        inicioinsc = results[0][16]
        fiminsc = results[0][17]      
        dt_inicioinsc = results[0][7]
        dt_fiminsc = results[0][8]     
        
        #return render_template('desafio200k.html', titulo=evento_titulo, modalidades=modalidades, vlSolo=vl200, 
        #                       vlDupla=vl100, vlQuarteto=vl50, vlOcteto=vl25, inicio_insc=inicioinsc, fim_insc=fiminsc)

        return render_template('desafio200k.html', titulo=evento_titulo, modalidades=modalidades, vlSolo=vl200, 
                               vlDupla=vl100, vlQuarteto=vl50, vlOcteto=vl25, inicio_insc=inicioinsc, fim_insc=fiminsc, 
                               dt_inicio_insc=dt_inicioinsc, dt_fim_insc=dt_fiminsc, dt_inicio_evento=dt_incio)

    except Exception as e:
        print(f"Erro ao carregar página: {str(e)}")
        return render_template('desafio200k.html', titulo="Erro ao carregar evento", modalidades=[])


@app.route('/get_modalidade_valores/<int:iditem>')
def get_modalidade_valores(iditem):
    try:
        cur = mysql.connection.cursor()
        cur.execute('''
            SELECT VLINSCRICAO, VLTAXA 
            FROM ecmrun.EVENTO_MODALIDADE 
            WHERE IDITEM = %s
        ''', (iditem,))
        
        result = cur.fetchone()
        cur.close()        

        if result:
            vlinscricao = float(result[0]) if result[0] else 0
            vltaxa = float(result[1]) if result[1] else 0

            # Store in session
            session['cat_vlinscricao'] = vlinscricao
            session['cat_vltaxa'] = vltaxa
            session['cat_iditem'] = iditem
            
            return jsonify({
                'vlinscricao': vlinscricao,
                'vltaxa': vltaxa,
                'iditem': iditem
            })

        else:
            return jsonify({
                'success': False,
                'message': 'Usuário ou senha inválidos'
            }), 401


    except Exception as e:
        print(f"Erro ao buscar valores da modalidade: {str(e)}")
        return jsonify({'error': str(e)}), 500


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

@app.route('/salvar-cadastro', methods=['POST'])
def salvar_cadastro():
    try:
        data = request.get_json()
        
        # Formatar a data de nascimento
        dia = str(data.get('dia_nasc')).zfill(2)  # Adiciona zero à esquerda se necessário
        mes = str(data.get('mes_nasc')).zfill(2)  # Converte o mês para número com dois dígitos
        ano = data.get('ano_nasc')
        data_nascimento = f"{dia}/{mes}/{ano}"
        
        # Gerar data e hora atual no formato requerido
        data_cadastro = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        # Criptografar a senha usando SHA-256
        senha = data.get('senha')
        senha_hash = hashlib.sha256(senha.encode()).hexdigest()
        
        # Preparar query e parâmetros
        query = """
        INSERT INTO ecmrun.ATLETA (
            CPF, NOME, SOBRENOME, DTNASCIMENTO, NRCELULAR, SEXO, EMAIL, TEL_EMERGENCIA, 
            CONT_EMERGENCIA, SENHA, ATIVO, DTCADASTRO, ESTADO, ID_CIDADE
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        """
        
        # Remover caracteres não numéricos do CPF e telefones
        cpf_limpo = re.sub(r'\D', '', data.get('cpf'))
        celular_limpo = re.sub(r'\D', '', data.get('celular'))
        tel_emergencia_limpo = re.sub(r'\D', '', data.get('telefone_emergencia')) if data.get('telefone_emergencia') else None
        
        params = (
            cpf_limpo,
            data.get('primeiro_nome').upper(),
            data.get('sobrenome').upper(),
            data_nascimento,
            celular_limpo,
            data.get('sexo'),
            data.get('email'),
            tel_emergencia_limpo,
            data.get('contato_emergencia').upper() if data.get('contato_emergencia') else None,
            senha_hash,
            'S',  # ATIVO
            data_cadastro,
            data.get('estado'),
            data.get('cidade')
        )

        #data.get('equipe').upper() if data.get('equipe') else None,
        
        # Executar a query
        cur = mysql.connection.cursor()
        cur.execute(query, params)
        mysql.connection.commit()
        cur.close()
        
        return jsonify({
            'success': True,
            'message': 'Cadastro realizado com sucesso!'
        })
        
    except Exception as e:
        print(f"Erro ao salvar cadastro: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Erro ao realizar cadastro. Por favor, tente novamente.'
        }), 500


@app.route('/enviar-codigo-verificacao', methods=['POST'])
def enviar_codigo_verificacao():
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'success': False, 'message': 'Email não fornecido'}), 400

        # Gerar código de verificação
        verification_code = str(random.randint(1000, 9999))
        
        # Armazenar na sessão
        session['verification_code'] = verification_code
        session['verification_email'] = email
        
        # Simplificar o remetente
        #sender = 'adm@ecmrun.com.br'
        sender = "ECM RUN <adm@ecmrun.com.br>"

        # Criar mensagem com configuração mais simples
        msg = Message(
            'Código de Verificação - ECM Run',
            sender=sender,
            recipients=[email]
        )

        # Template HTML do email
        msg.html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #4376ac;">Verificação de Cadastro - ECM Run</h2>
            <p>Olá,</p>
            <p>Seu código de verificação é:</p>
            <h1 style="color: #4376ac; font-size: 32px; letter-spacing: 5px;">{verification_code}</h1>
            <p>Este código é válido por 10 minutos.</p>
            <p>Se você não solicitou este código, por favor ignore este email.</p>
            <br>
            <p>Atenciosamente,<br>Equipe ECM Run</p>
        </div>
        """

        # Adicionar logs para debug
        print(f'Tentando enviar email para: {email}')
        print(f'Código de verificação: {verification_code}')
        
        # Enviar email com tratamento de erro específico
        try:
            mail.send(msg)
            print('Email enviado com sucesso')
        except Exception as mail_error:
            print(f'Erro ao enviar email: {str(mail_error)}')
            return jsonify({
                'success': False,
                'message': f'Erro ao enviar email: {str(mail_error)}'
            }), 500

        return jsonify({
            'success': True,
            'message': 'Código de verificação enviado com sucesso'
        })
        
    except Exception as e:
        print(f"Erro geral na rota: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro ao processar requisição: {str(e)}'
        }), 500
    

@app.route('/verificar-codigo', methods=['POST'])
def verificar_codigo():
    try:
        data = request.get_json()
        codigo_informado = data.get('codigo')
        senha = data.get('senha')
        
        codigo_correto = session.get('verification_code')
        email = session.get('verification_email')
        
        if not codigo_correto or not email:
            return jsonify({
                'success': False,
                'message': 'Sessão expirada. Por favor, solicite um novo código.'
            }), 400
        
        if codigo_informado != codigo_correto:
            return jsonify({
                'success': False,
                'message': 'Código inválido'
            }), 400
            
        # Aqui você pode adicionar o código para salvar o usuário no banco de dados
        # com a senha criptografada
        
        # Limpar dados da sessão
        session.pop('verification_code', None)
        session.pop('verification_email', None)
        
        return jsonify({
            'success': True,
            'message': 'Código verificado com sucesso'
        })
        
    except Exception as e:
        print(f"Erro ao verificar código: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Erro ao verificar código'
        }), 500

# Email sending function
def send_verification_email(email, code):
    try:
        
        if not email:
            return jsonify({'success': False, 'message': 'Email não fornecido'}), 400

        # Gerar código de verificação
        #verification_code = str(random.randint(1000, 9999))
        
        # Armazenar na sessão
        session['code'] = code
        session['verif_email'] = email
        
        # Simplificar o remetente
        #sender = 'adm@ecmrun.com.br'
        sender = "ECM RUN <adm@ecmrun.com.br>"

        # Criar mensagem com configuração mais simples
        msg = Message(
            'Redefinição de Senha - ECM Run',
            sender=sender,
            recipients=[email]
        )

        # Template HTML do email
        msg.html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #4376ac;">Verificação de Cadastro - ECM Run</h2>
            <p>Olá,</p>
            <p>Seu código de verificação para redefinição de senha é::</p>
            <h1 style="color: #4376ac; font-size: 32px; letter-spacing: 5px;">{code}</h1>
            <p>Este código é válido por 10 minutos.</p>
            <p>Se você não solicitou este código, por favor ignore este email.</p>
            <br>
            <p>Atenciosamente,<br>Equipe ECM Run</p>
        </div>
        """

        # Adicionar logs para debug
        print(f'Tentando enviar email para: {email}')
        print(f'Código de verificação: {code}')
        
        # Enviar email com tratamento de erro específico
        try:
            mail.send(msg)
            print('Email enviado com sucesso')
        except Exception as mail_error:
            print(f'Erro ao enviar email: {str(mail_error)}')
            return jsonify({
                'success': False,
                'message': f'Erro ao enviar email: {str(mail_error)}'
            }), 500

        return jsonify({
            'success': True,
            'message': 'Código de verificação enviado com sucesso'
        })
        
    except Exception as e:
        print(f"Erro geral na rota: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro ao processar requisição: {str(e)}'
        }), 500


@app.route('/recuperar-senha', methods=['GET'])
def recuperar_senha():
    return render_template('recuperar_senha.html')

@app.route('/verificar-usuario', methods=['POST'])
def verificar_usuario():
    cpf_email = request.json.get('cpf_email')

    cur = mysql.connection.cursor()    
    if '@' in cpf_email:
        # Query for email
        cur.execute("""
            SELECT IDATLETA, EMAIL 
            FROM ATLETA
            WHERE EMAIL = %s OR CPF = %s
            """, (cpf_email, cpf_email))
    else:
        # Remove non-numeric characters from CPF
        cpf = ''.join(filter(str.isdigit, cpf_email))    
        cur.execute("""
            SELECT IDATLETA, EMAIL 
            FROM ATLETA
            WHERE EMAIL = %s OR CPF = %s
            """, (cpf, cpf))

    result = cur.fetchone()
    print(f'SQL: {result}')
        

    if result:
        # Generate verification code
        verification_code = str(random.randint(1000, 9999))
        
        # Store the code and user ID in session
        session['code'] = verification_code
        session['user_id'] = result[0]
        
        print(f'CODIGO: {verification_code}')
        print(f'IDATLETA: {result[0]}')
        
        # Send verification code via email
        if send_verification_email(result[1], verification_code):
            return jsonify({
                'success': True,
                'message': 'Código de verificação enviado para seu email.'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Erro ao enviar email. Tente novamente.'
            })
    
    return jsonify({
        'success': False,
        'message': 'Usuário não encontrado.'
    })

@app.route('/verificar-codigo2', methods=['POST'])
def verificar_codigo2():
    codigo = request.json.get('codigo')
    stored_code = session.get('code')
    print(f'CODIGO DIGITADO: {codigo}')
    print(f'STORED CODE:  {stored_code}')
    
    if codigo == stored_code:
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Código inválido.'})


@app.route('/alterar-senha', methods=['POST'])
def alterar_senha():
    nova_senha = request.json.get('senha')
    user_id = session.get('user_id')
    senha_hash = hashlib.sha256(nova_senha.encode()).hexdigest()
    
    if not user_id:
        return jsonify({
            'success': False,
            'message': 'Sessão expirada. Tente novamente.'
        })
        
    try:

        cur = mysql.connection.cursor()    
        cur.execute("""
            UPDATE ATLETA
            SET SENHA = %s 
            WHERE IDATLETA = %s
            """, (senha_hash, user_id))

        mysql.connection.commit()
        
        # Clear session
        session.pop('code', None)
        session.pop('user_id', None)
        
        return jsonify({
            'success': True,
            'message': 'Senha alterada com sucesso!'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'Erro ao alterar senha. Tente novamente.'
        })
    finally:
        cur.close()

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

@app.route('/formulario200k')
def formulario200k():
    return render_template('formulario200k.html')

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
        cur.execute('SELECT IDATLETA FROM ecmrun.ATLETA WHERE CPF = %s', (cpf,))
        result = cur.fetchone()
        cur.close()
        
        return jsonify({'exists': bool(result)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def send_email(receipt_data):
    try:
        # Recuperar o email do atleta do banco de dados
        cur = mysql.connection.cursor()
        cur.execute('''
            SELECT A.EMAIL
            FROM ecmrun.ATLETA A
            JOIN ecmrun.INSCRICAO I ON I.IDATLETA = A.IDATLETA
            WHERE I.IDPAGAMENTO = %s
        ''', (receipt_data['inscricao'],))
        
        email_result = cur.fetchone()
        cur.close()

        if not email_result or not email_result[0]:
            app.logger.error("Email do atleta não encontrado")
            return False

        recipient_email = email_result[0]
        
        msg = Message(
            f'Comprovante de Inscrição - ID {receipt_data["inscricao"]}',
            sender=('ECM Run', 'adm@ecmrun.com.br'),
            recipients=[recipient_email]
        )
        
        msg.html = render_template('comprovante_email.html', **receipt_data)
        mail.send(msg)
        return True
        
    except Exception as e:
        app.logger.error(f"Erro ao enviar email: {str(e)}")
        return False


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
            SELECT l.id_logradouro, l.CEP, upper(l.descricao) as descricao, l.UF, l.complemento, 
                   upper(l.descricao_sem_numero) as descricao_sem_numero, 
                   upper(l.descricao_cidade) as descricao_cidade,
                   upper(l.descricao_bairro) as descricao_bairro, upper(e.nome) as estado
            FROM ecmrun.logradouro l, ecmrun.estado e
            WHERE e.uf = l.UF AND l.CEP =  %s
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
                    'descricao_bairro': result[7],
                    'estado': result[8]
                }
            })
        else:
            return jsonify({'success': False, 'message': 'CEP não encontrado'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/autenticar-login', methods=['POST'])
def autenticar_login():
    try:
        data = request.get_json()
        cpf_email = data.get('cpf_email')
        senha = data.get('senha')
        
        # Hash the password for comparison
        senha_hash = hashlib.sha256(senha.encode()).hexdigest()
        
        cur = mysql.connection.cursor()
        
        # Verifique se a entrada é e-mail ou CPF e consulte adequadamente
        if '@' in cpf_email:
            # Query for email
            cur.execute("""
                SELECT 
                    COALESCE(A.NOME, '') AS NOME, 
                    COALESCE(A.SOBRENOME, '') AS SOBRENOME, 
                    COALESCE(A.EMAIL, '') AS EMAIL, 
                    COALESCE(A.CPF, '') AS CPF, 
                    COALESCE(A.DTNASCIMENTO, '') AS DTNASCIMENTO, 
                    COALESCE(A.NRCELULAR, '') AS NRCELULAR, 
                    COALESCE(A.SEXO, '') AS SEXO, 
                    COALESCE(A.IDATLETA, '') AS IDATLETA, 
                    COALESCE(M.DESCRICAO, '') AS MODALIDADE, 
                    COALESCE(I.IDEVENTO, '') AS IDEVENTO, 
                    COALESCE(I.APOIO, '') AS APOIO, 
                    COALESCE(I.NOME_EQUIPE, '') AS NOME_EQUIPE,
                    COALESCE(I.INTEGRANTES, '') AS INTEGRANTES,
                    COALESCE(I.CAMISETA, '') AS CAMISETA,
                    COALESCE(I.VALOR, '') AS VALOR,
                    COALESCE(I.TAXA, '') AS TAXA,
                    COALESCE(I.VALOR_PGTO, '') AS VALOR_PGTO,
                    COALESCE(I.DTPAGAMENTO, '') AS DTPAGAMENTO,
                    COALESCE(I.FORMAPGTO, '') AS FO
