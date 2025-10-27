from flask import Flask, render_template, redirect, request, send_file, make_response, jsonify, flash, session, url_for
from datetime import datetime, timedelta
from flask_mail import Mail, Message
from flask_cors import CORS
from flask_mysqldb import MySQL
from dotenv import load_dotenv
from pytz import timezone
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.colors import black
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import secrets
import mercadopago
import requests
import hashlib
import pdfkit
import os
import io
import base64
import re
import random
import string
import json
import uuid
import logging
import pytz

load_dotenv()  # Carrega as variáveis do arquivo .env

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

sdk = mercadopago.SDK(os.getenv('MP_ACCESS_TOKEN'))

app.secret_key = os.getenv('SECRET_KEY')
CORS(app)

app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')  # Substitua pelo seu servidor SMTP
app.config['MAIL_PORT'] = os.getenv('MAIL_PORT') 
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME') 
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD') 
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')
app.config['MAIL_USE_TLS'] = True 
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_MAX_EMAILS'] = None
app.config['MAIL_TIMEOUT'] = 10  # segundos
app.config['MP_ACCESS_TOKEN'] = os.getenv('MP_ACCESS_TOKEN')

mail = Mail(app)

# Configuração MySQL
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB')
app.config['MYSQL_CHARSET'] = 'utf8mb4'

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

####### TESTE PARA CARTÁO ##################

# SOLUÇÃO 1: Middleware para adicionar CSP em todas as rotas
@app.after_request
def after_request(response):
    # CSP corrigida para Mercado Pago
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://secure.mlstatic.com https://sdk.mercadopago.com https://*.mercadopago.com; "
        "connect-src 'self' https://api.mercadopago.com https://*.mercadopago.com https://api.mercadolibre.com https://*.mercadolibre.com; "
        "frame-src 'self' https://*.mercadopago.com https://*.mercadolibre.com; "
        "img-src 'self' data: https: http:; "
        "style-src 'self' 'unsafe-inline' https://*.mercadopago.com; "
        "font-src 'self' https: data:;"
    )
    response.headers['Content-Security-Policy'] = csp
    return response

# SOLUÇÃO 2: Decorator para rotas específicas
def add_csp_header(f):
    def decorated_function(*args, **kwargs):
        resp = f(*args, **kwargs)
        if hasattr(resp, 'headers'):
            csp = (
                "default-src 'self'; "
                "connect-src 'self' https://api.mercadopago.com https://*.mercadopago.com https://api.mercadolibre.com https://*.mercadolibre.com; "
                "frame-src 'self' https://*.mercadopago.com https://*.mercadolibre.com;"
            )
            resp.headers['Content-Security-Policy'] = csp
        return resp
    return decorated_function

###########################

# ANTIGA - VERIFICAR SE APAGA
@app.route('/obter_eventos_ativos', methods=['GET'])
def obter_eventos_ativos():
    """Rota para obter eventos ativos para exibição na página principal"""
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT IDEVENTO, DESCRICAO, 
                CASE WHEN DTINICIO=DTFIM 
                    THEN DTINICIO ELSE CONCAT(DTINICIO,' - ',DTFIM)
                END AS DTEVENTO, 
                CONCAT(SUBSTR(INICIO_INSCRICAO,1,10),' A ',
                       SUBSTR(FIM_INSCRICAO,1,10)) AS PERIODO_INSCRICAO,
                ROTA
            FROM EVENTO_1
            WHERE ATIVO = 'S' AND IDORGANIZADOR = 2
            ORDER BY DTINICIO
        """)
        
        # Busca todos os eventos
        eventos = cur.fetchall()
        cur.close()
        
        # Converte os resultados para uma lista de dicionários
        eventos_lista = []
        if eventos:
            for evento in eventos:
                evento_dict = {
                    'IDEVENTO': evento[0],
                    'DESCRICAO': evento[1],
                    'DTEVENTO': evento[2],
                    'PERIODO_INSCRICAO': evento[3],
                    'ROTA': evento[4]
                }
                eventos_lista.append(evento_dict)
        
        return jsonify({
            'success': True,
            'eventos': eventos_lista,
            'total': len(eventos_lista)
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erro ao obter eventos ativos: {str(e)}',
            'eventos': []
        }), 500


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/cobranca")
def cobranca():
    return render_template("cobranca.html")


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
@add_csp_header
def checkout():

    # Get values from session
    vlinscricao = session.get('valoratual', 0)
    vltaxa = session.get('valortaxa', 0)
    valor_total = float(vlinscricao) + float(vltaxa)
    
    # Obter a chave pública do Mercado Pago das variáveis de ambiente
    mp_public_key = os.environ.get('MP_PUBLIC_KEY')
    
    return render_template('checkout.html', 
                         valor_inscricao=vlinscricao,
                         valor_taxa=vltaxa,
                         valor_total=valor_total,
                         mp_public_key=mp_public_key)


@app.route('/process_payment', methods=['POST'])
def process_payment():
    payment_id = None
    payer_cpf = None  # CORREÇÃO: definir variável antes de usar
    inscrito_cpf = None
    
    try:
        app.logger.info("=== INÍCIO DO PROCESSAMENTO DE PAGAMENTO ===")
        payment_data = request.json
        
        # CORREÇÃO: extrair CPFs logo no início
        payer_cpf = payment_data.get('CPF')  # CPF do PAGADOR
        inscrito_cpf = payment_data.get('inscrito_cpf')  # CPF do INSCRITO
        device_id = payment_data.get('device_id')
        
        # Log dados recebidos (sem informações sensíveis)
        safe_data = {**payment_data}
        if 'token' in safe_data:
            safe_data['token'] = '***HIDDEN***'
        if 'payer' in safe_data and 'identification' in safe_data['payer']:
            safe_data['payer']['identification']['number'] = '***HIDDEN***'
        app.logger.info(f"Dados recebidos: {safe_data}")
        
        # Extract data with proper error handling
        try:
            installments = int(payment_data.get('installments', 1))
            transaction_amount = float(payment_data.get('transaction_amount', 0))
            
            # Round to 2 decimal places to avoid floating point precision issues
            valor_total = round(float(payment_data.get('valor_total', 0)), 2)
            valor_atual = round(float(payment_data.get('valor_atual', 0)), 2)
            valor_taxa = round(float(payment_data.get('valor_taxa', 0)), 2)
            
            app.logger.info(f"Valores processados - Inscrito CPF: {inscrito_cpf}, Pagador CPF: {payer_cpf}, Device ID: {device_id}, Valor Total: R$ {valor_total}, Valor Atual: R$ {valor_atual}, Valor Taxa: R$ {valor_taxa}, Parcelas: {installments}")

            # Ensure transaction_amount matches valor_total
            if abs(transaction_amount - valor_total) > 0.01:
                app.logger.warning(f"DISCREPÂNCIA DE VALORES - Pagador CPF: {payer_cpf}, transaction_amount: R$ {transaction_amount}, valor_total: R$ {valor_total}")
                # Use valor_total as the source of truth
                transaction_amount = valor_total
                
        except (ValueError, TypeError) as e:
            app.logger.error(f"ERRO AO PROCESSAR VALORES - Pagador CPF: {payer_cpf}, Erro: {str(e)}")
            raise ValueError(f"Erro ao processar valores numéricos: {str(e)}")

        # Store session data
        session['valorTotal'] = transaction_amount
        session['numeroParcelas'] = installments
        session['valorParcela'] = transaction_amount / installments if installments > 0 else transaction_amount
        session['valorTotalsemJuros'] = valor_total
        session['valorAtual'] = valor_atual
        session['valorTaxa'] = valor_taxa
        session['formaPagto'] = 'CARTÃO DE CRÉDITO'
        session['CPF'] = inscrito_cpf  # Manter CPF do inscrito para compatibilidade
        session['payer_CPF'] = payer_cpf  # Novo campo para logs
        session['deviceId'] = device_id

        # Validar dados recebidos
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
                app.logger.error(f"CAMPO OBRIGATÓRIO AUSENTE - Pagador CPF: {payer_cpf}, Campo: {field}")
                raise ValueError(f"Campo obrigatório ausente: {field}")
        
        # Validate payer data
        if not payment_data['payer'].get('email'):
            app.logger.error(f"EMAIL AUSENTE - Pagador CPF: {payer_cpf}")
            raise ValueError("Email do pagador é obrigatório")
        
        if 'identification' not in payment_data['payer']:
            app.logger.error(f"IDENTIFICAÇÃO AUSENTE - Pagador CPF: {payer_cpf}")
            raise ValueError("Identificação do pagador é obrigatória")
        
        if not payment_data['payer']['identification'].get('type') or not payment_data['payer']['identification'].get('number'):
            app.logger.error(f"DOCUMENTO INVÁLIDO - Pagador CPF: {payer_cpf}")
            raise ValueError("Tipo e número de documento são obrigatórios")

        # Validate device ID
        if not device_id or len(device_id.strip()) < 10:
            app.logger.error(f"DEVICE ID INVÁLIDO - Pagador CPF: {payer_cpf}, Device ID: {device_id}")
            raise ValueError("Device ID é obrigatório e deve ter pelo menos 10 caracteres")

        app.logger.info(f"VALIDAÇÃO CONCLUÍDA - Pagador CPF: {payer_cpf}, Device ID: {device_id}, Email: {payment_data['payer']['email']}, Método: {payment_data['payment_method_id']}")

        # Gerar referência externa única
        external_reference = str(uuid.uuid4())
        app.logger.info(f"REFERÊNCIA EXTERNA GERADA - Pagador CPF: {payer_cpf}, Ref: {external_reference}")
        
        # Criar preferência de pagamento
        item_details = {
            "id": "ECM RUN TICKETS",
            "title": "Inscrição de Evento",
            "description": "Inscrição de Corrida",
            "category_id": "SPORTS_EVENT",
            "quantity": 1,
            "currency_id": "BRL",
            "unit_price": valor_atual,
            "total_amount": transaction_amount
        }
        
        # Preparar preferência de pagamento
        preference_data = {
            "items": [item_details],
            "notification_url": "https://ecmrun.com.br/webhook",
            "external_reference": external_reference
        }
        
        # Criar preferência
        try:
            app.logger.info(f"CRIANDO PREFERÊNCIA - Pagador CPF: {payer_cpf}")
            preference_response = sdk.preference().create(preference_data)
            
            if "response" not in preference_response:
                error_message = preference_response.get("message", "Erro desconhecido na criação da preferência")
                app.logger.error(f"ERRO NA PREFERÊNCIA - Pagador CPF: {payer_cpf}, Erro: {error_message}")
                raise ValueError(f"Erro ao criar preferência de pagamento: {error_message}")
                
            app.logger.info(f"PREFERÊNCIA CRIADA COM SUCESSO - Pagador CPF: {payer_cpf}")
            
        except Exception as e:
            app.logger.error(f"EXCEÇÃO NA PREFERÊNCIA - Pagador CPF: {payer_cpf}, Erro: {str(e)}")
            raise ValueError(f"Erro ao criar preferência de pagamento: {str(e)}")
		
		##### adicionado pra teste
		# Buscar nome do evento do request
		id_evento = payment_data.get('id_evento')
		statement_text = f"ECMRUN EVT{id_evento}" if id_evento else "ECMRUN TICKETS"
		##### fim adicionado pra teste 
		
		# CORREÇÃO: Estrutura de pagamento sem device_id duplicado
        payment_info = {
            "transaction_amount": transaction_amount,
            "token": payment_data['token'],
            "description": "Inscrição Corrida",
            # "statement_descriptor": "ECMRUN TICKETS", removido pra teste
			"statement_descriptor": statement_text[:22],  #adicionado pra teste
            "installments": installments,
            "payment_method_id": payment_data['payment_method_id'],
            "external_reference": external_reference,
            "notification_url": "https://ecmrun.com.br/webhook",
            # REMOVIDO device_id daqui - será apenas no additional_info
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
                "items": [{
                    "id": "ECM RUN TICKETS",
                    "title": "Inscrição de Evento",
                    "description": "Inscrição de corrida",
                    "category_id": "SPORTS_EVENT",
                    "quantity": 1,
                    "unit_price": valor_atual
                }],
                "payer": {
                    "first_name": payment_data['payer']['first_name'],
                    "last_name": payment_data['payer']['last_name'],
                    "registration_date": datetime.now().isoformat()
                    # REMOVIDO device_id daqui também
                },
                "ip_address": request.remote_addr
                # REMOVIDO device_id daqui também
            }
        }

        # Log payment info (exclude sensitive data)
        safe_payment_info = {**payment_info}
        safe_payment_info['token'] = '***HIDDEN***'
        safe_payment_info['payer']['identification']['number'] = '***HIDDEN***'
        app.logger.info(f"ENVIANDO PAGAMENTO PARA MERCADOPAGO - Pagador CPF: {payer_cpf}, Device ID: {device_id}")
        app.logger.debug(f"Dados do pagamento: {safe_payment_info}")

        # Processar pagamento
        try:
            app.logger.info(f"PROCESSANDO PAGAMENTO - Pagador CPF: {payer_cpf}, Device ID: {device_id}, Valor: R$ {transaction_amount}, Método: {payment_data['payment_method_id']}")
            payment_response = sdk.payment().create(payment_info)
            
            app.logger.info(f"RESPOSTA RECEBIDA DO MERCADOPAGO - Pagador CPF: {payer_cpf}, Device ID: {device_id}")
            app.logger.debug(f"Resposta completa: {payment_response}")
            
            if "response" not in payment_response:
                error_details = payment_response.get("cause", [{}])
                error_message = "Erro desconhecido"
                
                if isinstance(error_details, list) and len(error_details) > 0:
                    error_message = error_details[0].get("description", "Erro desconhecido")
                    error_code = error_details[0].get("code", "unknown")
                    app.logger.error(f"ERRO NO PAGAMENTO - Pagador CPF: {payer_cpf}, Device ID: {device_id}, Código: {error_code}, Mensagem: {error_message}")
                else:
                    app.logger.error(f"ERRO NO PAGAMENTO - Pagador CPF: {payer_cpf}, Device ID: {device_id}, Detalhes: {error_details}")
                
                return jsonify({
                    "error": "Erro ao processar pagamento",
                    "details": error_message
                }), 400
                
            payment_result = payment_response["response"]
            payment_id = payment_result.get("id")
            status = payment_result.get("status")
            status_detail = payment_result.get("status_detail")
            
            # Log detalhado do resultado do pagamento
            if status == "approved":
                app.logger.info(f"🎉 PAGAMENTO APROVADO - Pagador CPF: {payer_cpf}, Device ID: {device_id}, ID: {payment_id}, Valor: R$ {transaction_amount}, Método: {payment_data['payment_method_id']}")
                
            elif status == "pending":
                app.logger.warning(f"⏳ PAGAMENTO PENDENTE - Pagador CPF: {payer_cpf}, Device ID: {device_id}, ID: {payment_id}, Status Detail: {status_detail}, Valor: R$ {transaction_amount}")
                
            elif status == "rejected":
                app.logger.error(f"❌ PAGAMENTO RECUSADO - Pagador CPF: {payer_cpf}, Device ID: {device_id}, ID: {payment_id}, Motivo: {status_detail}, Valor: R$ {transaction_amount}, Método: {payment_data['payment_method_id']}")
                
                # Log adicional para recusas com mais detalhes
                if payment_result.get("failure_reason"):
                    app.logger.error(f"MOTIVO DA RECUSA - Pagador CPF: {payer_cpf}, Device ID: {device_id}, ID: {payment_id}, Failure Reason: {payment_result.get('failure_reason')}")
                
                if payment_result.get("gateway_rejection_reason"):
                    app.logger.error(f"REJEIÇÃO DO GATEWAY - Pagador CPF: {payer_cpf}, Device ID: {device_id}, ID: {payment_id}, Gateway Reason: {payment_result.get('gateway_rejection_reason')}")
                    
            else:
                app.logger.warning(f"❓ STATUS DESCONHECIDO - Pagador CPF: {payer_cpf}, Device ID: {device_id}, ID: {payment_id}, Status: {status}, Status Detail: {status_detail}")

            # Log informações adicionais importantes
            if payment_result.get("fee_details"):
                total_fees = sum([fee.get("amount", 0) for fee in payment_result["fee_details"]])
                app.logger.info(f"TAXAS APLICADAS - Pagador CPF: {payer_cpf}, Device ID: {device_id}, ID: {payment_id}, Total em Taxas: R$ {total_fees}")
                
            if payment_result.get("installments", 0) > 1:
                app.logger.info(f"PARCELAMENTO - Pagador CPF: {payer_cpf}, Device ID: {device_id}, ID: {payment_id}, Parcelas: {payment_result.get('installments')}")

            app.logger.info(f"=== PROCESSAMENTO CONCLUÍDO - Pagador CPF: {payer_cpf}, Device ID: {device_id}, ID: {payment_id}, Status: {status} ===")
            
            return jsonify(payment_result), 200        
            
        except Exception as e:
            app.logger.error(f"🔥 EXCEÇÃO NO PAGAMENTO - Pagador CPF: {payer_cpf}, Device ID: {device_id}, Erro: {str(e)}, Tipo: {type(e).__name__}")
            app.logger.exception("Stack trace completo:")
            return jsonify({
                "error": "Erro ao processar pagamento",
                "details": str(e)
            }), 400
        
    except ValueError as e:
        app.logger.error(f"ERRO DE VALIDAÇÃO - Pagador CPF: {payer_cpf}, Device ID: {payment_data.get('device_id', 'N/A') if 'payment_data' in locals() else 'N/A'}, Erro: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        app.logger.error(f"🔥 ERRO GERAL NO PROCESSAMENTO - Pagador CPF: {payer_cpf}, Device ID: {payment_data.get('device_id', 'N/A') if 'payment_data' in locals() else 'N/A'}, Payment ID: {payment_id}, Erro: {str(e)}")
        app.logger.exception("Stack trace completo:")
        return jsonify({"error": str(e)}), 400
		

def send_organizer_notification(receipt_data):
    try:
        msg = Message(
            f'Nova Inscrição - {receipt_data["evento"]} - ID {receipt_data["inscricao"]}',
            sender=('ECM Run', 'ecmsistemasdeveloper@gmail.com'),
            recipients=['kelioesteves@hotmail.com']
            #recipients=['naicm12@gmail.com']
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
    
    # Antes de redirecionar para pagamento, armazenar a página de origem
    pagina_origem = session.get('pagina_origem')  # Já estava armazenada no sistema de token
    if pagina_origem:
        session['pagina_evento_origem'] = pagina_origem
        
    try:
        app.logger.info(f"Payment ID: {payment_id}")
        
        cur = mysql.connection.cursor()
        
        cur.execute('''
            SELECT ei.DTPAGAMENTO, e.TITULO, e.ENDERECO, 
                e.DATAINICIO, e.DATAFIM, e.HRINICIO,
                CONCAT(ei.NOME, ' ', ei.SOBRENOME) AS NOME_COMPLETO, 
                CASE WHEN i.KM = 0
                    THEN i.MODALIDADE
                    ELSE CONCAT(i.KM, ' KM') 
                END AS KM_DESCRICAO, 
                ei.VLINSCRICAO, ei.VLTOTAL, ei.FORMAPGTO, 
                ei.IDPAGAMENTO, ei.FLEMAIL, ei.IDINSCRICAO, 
                e.OBS, ei.CPF, ei.DTNASCIMENTO 
            FROM EVENTO_INSCRICAO ei
            INNER JOIN EVENTO1 e ON e.IDEVENTO = ei.IDEVENTO
            INNER JOIN EVENTO_ITEM i ON i.IDITEM = ei.IDITEMEVENTO
            WHERE ei.STATUS = 'A' 
            AND ei.IDPAGAMENTO = %s 
        ''', (payment_id,))
        
        receipt_data = cur.fetchone()
        cur.close()

        if not receipt_data:
            app.logger.info("Dados não encontrados")
            return "Dados não encontrados", 404
        
        # Obter os dados como datetime do MySQL
        data_pagamento = receipt_data[0]
        data_inicio = receipt_data[3]
        data_fim = receipt_data[4]
        hr_inicio = receipt_data[5]

        # Formatar data de pagamento
        if isinstance(data_pagamento, datetime):
            data_formatada = data_pagamento.strftime('%d/%m/%Y %H:%M:%S')
        else:
            data_formatada = str(data_pagamento)

        # Formatar hora de início (já vem como string)
        hora_formatada = str(hr_inicio)

        # Formatar data do evento
        if hasattr(data_inicio, 'strftime') and hasattr(data_fim, 'strftime'):
            if data_inicio == data_fim:
                # Mesmo dia
                data_evento = f"{data_inicio.strftime('%d/%m/%Y')} {hora_formatada}"
            else:
                # Dias diferentes
                data_evento = f"{data_inicio.strftime('%d/%m/%Y')} {hora_formatada} - {data_fim.strftime('%d/%m/%Y')}"
        else:
            # Fallback se não for date/datetime
            data_evento = f"{data_inicio} {hora_formatada}"

        # Estruturar os dados do comprovante
        receipt_data_dict = { 
            'data': data_formatada,
            'evento': receipt_data[1],
            'endereco': receipt_data[2],
            'dataevento': data_evento,
            'participante': receipt_data[6],
            'km': receipt_data[7],
            'valor': f'R$ {receipt_data[8]:,.2f}',  # Formatar valor
            'valortotal': f'R$ {receipt_data[9]:,.2f}',  # Formatar valor
            'formapgto': receipt_data[10],
            'inscricao': str(receipt_data[11]),
            'obs': receipt_data[14] if receipt_data[14] is not None else ''  # Evita mostrar None
        }
        
        app.logger.info("Dados da Inscrição:")
        app.logger.info(receipt_data)

        flemail = receipt_data[12]
        id_inscricao = receipt_data[13]
        app.logger.info(f' FLEMAIL: { flemail }')
        app.logger.info(f' ID INSC: { id_inscricao }')

        if flemail == 'N':

            # Enviar email com os dados do comprovante
            send_email(receipt_data_dict)
        
            # Enviar notificação para o organizador
            send_organizer_notification(receipt_data_dict)

            cur1 = mysql.connection.cursor()
            cur1.execute('''
                UPDATE EVENTO_INSCRICAO SET FLEMAIL = 'S'
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
        
        cur.execute('''
            SELECT ei.DTPAGAMENTO, e.TITULO, e.ENDERECO, 
                e.DATAINICIO, e.DATAFIM, e.HRINICIO,
                CONCAT(ei.NOME, ' ', ei.SOBRENOME) AS NOME_COMPLETO, 
                CASE WHEN i.KM = 0
                    THEN i.MODALIDADE
                    ELSE CONCAT(i.KM, ' KM') 
                END AS KM_DESCRICAO, 
                ei.VLINSCRICAO, ei.VLTOTAL, ei.FORMAPGTO, 
                ei.IDPAGAMENTO, ei.FLEMAIL, ei.IDINSCRICAO, 
                e.OBS, ei.CPF, ei.DTNASCIMENTO 
            FROM EVENTO_INSCRICAO ei
            INNER JOIN EVENTO1 e ON e.IDEVENTO = ei.IDEVENTO
            INNER JOIN EVENTO_ITEM i ON i.IDITEM = ei.IDITEMEVENTO
            WHERE ei.STATUS = 'A' 
            AND ei.IDPAGAMENTO = %s 
        ''', (payment_id,))
        
        receipt_data = cur.fetchone()
        cur.close()

        if not receipt_data:
            app.logger.info("Dados não encontrados")
            return "Dados não encontrados", 404
        
        # Obter os dados como datetime do MySQL
        data_pagamento = receipt_data[0]
        data_inicio = receipt_data[3]
        data_fim = receipt_data[4]
        hr_inicio = receipt_data[5]

        # Formatar data de pagamento
        if isinstance(data_pagamento, datetime):
            data_formatada = data_pagamento.strftime('%d/%m/%Y %H:%M:%S')
        else:
            data_formatada = str(data_pagamento)

        # Formatar hora de início (já vem como string)
        hora_formatada = str(hr_inicio)

        # Formatar data do evento
        if hasattr(data_inicio, 'strftime') and hasattr(data_fim, 'strftime'):
            if data_inicio == data_fim:
                # Mesmo dia
                data_evento = f"{data_inicio.strftime('%d/%m/%Y')} {hora_formatada}"
            else:
                # Dias diferentes
                data_evento = f"{data_inicio.strftime('%d/%m/%Y')} {hora_formatada} - {data_fim.strftime('%d/%m/%Y')}"
        else:
            # Fallback se não for date/datetime
            data_evento = f"{data_inicio} {hora_formatada}"

        # Estruturar os dados do comprovante
        receipt_data_dict = { 
            'data': data_formatada,
            'evento': receipt_data[1],
            'endereco': receipt_data[2],
            'dataevento': data_evento,
            'participante': receipt_data[6],
            'km': receipt_data[7],
            'valor': f'R$ {receipt_data[8]:,.2f}',  # Formatar valor
            'valortotal': f'R$ {receipt_data[9]:,.2f}',  # Formatar valor
            'formapgto': receipt_data[10],
            'inscricao': str(receipt_data[11]),
            'obs': receipt_data[14] if receipt_data[14] is not None else ''  # Evita mostrar None
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
        
        cur = mysql.connection.cursor()
        # Execute a SQL com o payment_id
        cur.execute('''
            SELECT ei.DTPAGAMENTO, e.TITULO, e.ENDERECO, 
                e.DATAINICIO, e.DATAFIM, e.HRINICIO,
                CONCAT(ei.NOME, ' ', ei.SOBRENOME) AS NOME_COMPLETO, 
                CASE WHEN i.KM = 0
                    THEN i.MODALIDADE
                    ELSE CONCAT(i.KM, ' KM') 
                END AS KM_DESCRICAO, 
                ei.VLINSCRICAO, ei.VLTOTAL, ei.FORMAPGTO, 
                ei.IDPAGAMENTO, ei.FLEMAIL, ei.IDINSCRICAO, 
                e.OBS, ei.CPF, ei.DTNASCIMENTO 
            FROM EVENTO_INSCRICAO ei
            INNER JOIN EVENTO1 e ON e.IDEVENTO = ei.IDEVENTO
            INNER JOIN EVENTO_ITEM i ON i.IDITEM = ei.IDITEMEVENTO
            WHERE ei.STATUS = 'A' 
            AND ei.IDPAGAMENTO = %s  
        ''', (payment_id,))
        
        receipt_data = cur.fetchone()
        cur.close()

        if not receipt_data:
            app.logger.info("Dados não encontrados")
            return "Dados não encontrados", 404
        
        # Obter os dados como datetime do MySQL
        data_pagamento = receipt_data[0]
        data_inicio = receipt_data[3]
        data_fim = receipt_data[4]
        hr_inicio = receipt_data[5]

        # Formatar data de pagamento
        if isinstance(data_pagamento, datetime):
            data_formatada = data_pagamento.strftime('%d/%m/%Y %H:%M:%S')
        else:
            data_formatada = str(data_pagamento)

        # Formatar hora de início (já vem como string)
        hora_formatada = str(hr_inicio)

        # Formatar data do evento
        if hasattr(data_inicio, 'strftime') and hasattr(data_fim, 'strftime'):
            if data_inicio == data_fim:
                # Mesmo dia
                data_evento = f"{data_inicio.strftime('%d/%m/%Y')} {hora_formatada}"
            else:
                # Dias diferentes
                data_evento = f"{data_inicio.strftime('%d/%m/%Y')} {hora_formatada} - {data_fim.strftime('%d/%m/%Y')}"
        else:
            # Fallback se não for date/datetime
            data_evento = f"{data_inicio} {hora_formatada}"

        # Estruturar os dados do comprovante
        receipt_data_dict = { 
            'data': data_formatada,
            'evento': receipt_data[1],
            'endereco': receipt_data[2],
            'dataevento': data_evento,
            'participante': receipt_data[6],
            'km': receipt_data[7],
            'valor': f'R$ {receipt_data[8]:,.2f}',  # Formatar valor
            'valortotal': f'R$ {receipt_data[9]:,.2f}',  # Formatar valor
            'formapgto': receipt_data[10],
            'inscricao': str(receipt_data[11]),
            'obs': receipt_data[14] if receipt_data[14] is not None else ''  # Evita mostrar None
        }
        
        app.logger.info("Dados da Inscrição:")
        app.logger.info(receipt_data)


        return render_template('comprovante_email.html', **receipt_data_dict)

    except Exception as e:
        app.logger.error(f"Erro ao buscar dados do comprovante: {str(e)}")
        return "Erro ao buscar dados", 500


@app.route('/get_evento_data')
def get_evento_data():
    try:
        cur = mysql.connection.cursor()
        cur.execute('''
            SELECT E.IDEVENTO, E.DESCRICAO, E.DTINICIO, E.DTFIM, E.HRINICIO,
                E.LOCAL, E.CIDADEUF, E.INICIO_INSCRICAO, E.FIM_INSCRICAO,
                M.IDITEM, M.DESCRICAO AS MODALIDADE, M.DISTANCIA, M.KM,
                M.VLINSCRICAO, M.VLMEIA, M.VLTAXA
            FROM EVENTO_1 E, EVENTO_MODALIDADE M
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
            FROM EVENTO_1 E, EVENTO_MODALIDADE M
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


@app.route('/autenticar', methods=['POST'])
def autenticar():
    email = request.form.get('email')
    cpf = request.form.get('cpf')
    categoria = request.form.get('categoria')

    verification_code = str(random.randint(1000, 9999))
    session['verification_code'] = verification_code
    
    return render_template('autenticar200k.html', verification_code=verification_code)

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
        #sender = 'ecmsistemasdeveloper@gmail.com'
        sender = "ECM RUN <ecmsistemasdeveloper@gmail.com>"

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


def send_email(receipt_data):
    try:
        # Recuperar o email do atleta do banco de dados
        cur = mysql.connection.cursor()
        cur.execute('''
            SELECT EMAIL FROM EVENTO_INSCRICAO
            WHERE IDPAGAMENTO = %s
        ''', (receipt_data['inscricao'],))
        
        email_result = cur.fetchone()
        cur.close()

        if not email_result or not email_result[0]:
            app.logger.error("Email do atleta não encontrado")
            return False

        recipient_email = email_result[0]
        
        msg = Message(
            f'Comprovante de Inscrição - ID {receipt_data["inscricao"]}',
            sender=('ECM Run', 'ecmsistemasdeveloper@gmail.com'),
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



@app.route('/pagamento')
def pagamento():

    # Antes de redirecionar para pagamento, armazenar a página de origem
    pagina_origem = session.get('pagina_origem')  # Já estava armazenada no sistema de token
    if pagina_origem:
        session['pagina_evento_origem'] = pagina_origem

    # Get values from session
    vlinscricao = session.get('valoratual', 0)
    vltaxa = session.get('valortaxa', 0)
    valor_total = float(vlinscricao) + float(vltaxa)
    
    return render_template('pagamento.html', 
                         valor_inscricao=vlinscricao,
                         valor_taxa=vltaxa,
                         valor_total=valor_total)


@app.route('/voltar-para-evento')
def voltar_para_evento():
    # Recupera a página de origem armazenada
    pagina_origem = session.get('pagina_evento_origem')
        
    # Se existe página de origem, redireciona para ela
    if pagina_origem:
        return redirect(pagina_origem)
    else:
        # Se não tem página de origem definida, redireciona para uma página padrão
        return redirect('/')  # ou qualquer página padrão que você queira

# @app.route('/gerar-pix', methods=['POST'])
# def gerar_pix():
#     try:
#         data = request.get_json()
#         # Add more robust validation and logging
#         print(f"Raw data received: {data}")
        
#         # More robust parsing with better error handling
#         try:
#             valor_total = round(float(data.get('valor_total', 0)), 2)
#             valor_atual = round(float(data.get('valor_atual', 0)), 2)
#             valor_taxa = round(float(data.get('valor_taxa', 0)), 2)
#         except (ValueError, TypeError) as e:
#             print(f"Error parsing values: {str(e)}")
#             print(f"valor_total: {data.get('valor_total')}, type: {type(data.get('valor_total'))}")
#             print(f"valor_atual: {data.get('valor_atual')}, type: {type(data.get('valor_atual'))}")
#             print(f"valor_taxa: {data.get('valor_taxa')}, type: {type(data.get('valor_taxa'))}")
            
#             # Try to convert from string with comma to float
#             try:
#                 valor_total = round(float(str(data.get('valor_total', '0')).replace(',', '.')), 2)
#                 valor_atual = round(float(str(data.get('valor_atual', '0')).replace(',', '.')), 2)
#                 valor_taxa = round(float(str(data.get('valor_taxa', '0')).replace(',', '.')), 2)
#                 print(f"After conversion: valor_total={valor_total}, valor_atual={valor_atual}, valor_taxa={valor_taxa}")
#             except Exception as conversion_error:
#                 print(f"Conversion attempt failed: {str(conversion_error)}")
#                 return jsonify({
#                     'success': False,
#                     'message': 'Erro ao processar valores. Verifique se os valores são numéricos válidos.'
#                 }), 400
        
#         # Store in session
#         session['valorTotal'] = valor_total
#         session['valorAtual'] = valor_atual
#         session['valorTaxa'] = valor_taxa
#         session['formaPagto'] = 'PIX'
        
#         # Validate minimum transaction amount
#         if valor_total < 1:
#             return jsonify({
#                 'success': False,
#                 'message': 'Valor mínimo da transação deve ser maior que R$ 1,00'
#             }), 400
        
#         print("=== DEBUG: Iniciando geração do PIX ===")
#         print(f"Valor total processado: {valor_total}")
#         print(f"Valor atual: {valor_atual}")
#         print(f"Valor taxa: {valor_taxa}")
        
#         # Get payer info and validate it's present
#         email = session.get('user_email')
#         nome_completo = session.get('user_name', '')
        
#         # Fallback to data from request if session is empty
#         if not email:
#             email = data.get('email')
#             print(f"Email not found in session, using from request: {email}")
        
#         if not nome_completo:
#             nome_completo = data.get('nome', '')
#             print(f"Nome not found in session, using from request: {nome_completo}")
            
#         nome_parts = nome_completo.split() if nome_completo else ['', '']
        
#         cpf = session.get('user_cpf')
#         if not cpf:
#             cpf = data.get('cpf')
#             print(f"CPF not found in session, using from request: {cpf}")
            
#         # Validate required fields
#         if not email:
#             return jsonify({
#                 'success': False,
#                 'message': 'Email do pagador é obrigatório'
#             }), 400
            
#         if not cpf:
#             return jsonify({
#                 'success': False,
#                 'message': 'CPF do pagador é obrigatório'
#             }), 400
            
#         # Clean CPF format
#         cpf_cleaned = re.sub(r'\D', '', cpf) if cpf else ""
#         session['CPF'] = cpf_cleaned

#         print(f"Dados do pagador finais:")
#         print(f"- Email: {email}")
#         print(f"- Nome: {nome_completo}")
#         print(f"- CPF: {cpf_cleaned}")

#         # Try to call email function safely
#         try:
#             fn_email(email)
#         except Exception as email_error:
#             print(f"Warning: Error in fn_email: {str(email_error)}")
#             # Continue processing even if email function fails

#         # Generate unique reference
#         external_reference = str(uuid.uuid4())

#         preference_data = {
#             "items": [{
#                 "id": "Pagamnento de Inscrição",
#                 "title": "ECM RUN - Inscrição",
#                 "description": "Inscrição Corrida",
#                 "category_id": "sports_tickets",
#                 "quantity": 1,
#                 "unit_price": valor_total
#             }],
#             "statement_descriptor": "ECMRUM_INSCRICAO"
#         }
        
#         preference_result = sdk.preference().create(preference_data)

#         # Create payment data
#         payment_data = {
#             "transaction_amount": float(valor_total),  # Ensure it's a float
#             "description": "ECM RUN - Inscrição",
#             "payment_method_id": "pix",
#             "payer": {
#                 "email": email,
#                 "first_name": nome_parts[0] if nome_parts else "",
#                 "last_name": " ".join(nome_parts[1:]) if len(nome_parts) > 1 else "",
#                 "identification": {
#                     "type": "CPF",
#                     "number": cpf_cleaned
#                 }   
#             },
#             "notification_url": "https://ecmrun.com.br/webhook",
#             "external_reference": external_reference
#         }
        
#         print("Dados do pagamento preparados:")
#         print(json.dumps(payment_data, indent=2))

#         # Create payment in Mercado Pago
#         print("Enviando requisição para o Mercado Pago...")
        
#         try:
#             payment_response = sdk.payment().create(payment_data)
#         except Exception as mp_error:
#             print(f"Erro na comunicação com Mercado Pago: {str(mp_error)}")
#             return jsonify({
#                 'success': False,
#                 'message': f'Erro na comunicação com o gateway de pagamento: {str(mp_error)}'
#             }), 500
        
#         print("Resposta do Mercado Pago recebida")
        
#         # Validate response structure
#         if not payment_response:
#             print("Erro: Resposta vazia do Mercado Pago")
#             return jsonify({
#                 'success': False,
#                 'message': 'Resposta vazia do gateway de pagamento'
#             }), 500
            
#         if "response" not in payment_response:
#             print(f"Erro: Formato de resposta inesperado: {payment_response}")
#             return jsonify({
#                 'success': False,
#                 'message': 'Formato de resposta inesperado do gateway de pagamento'
#             }), 500

#         payment = payment_response["response"]
        
#         # Check for error in response
#         if "error" in payment:
#             print(f"Erro retornado pelo Mercado Pago: {payment}")
#             return jsonify({
#                 'success': False,
#                 'message': f'Erro do gateway de pagamento: {payment.get("message", "Erro desconhecido")}'
#             }), 400
        
#         # Check for QR code data
#         if "point_of_interaction" not in payment:
#             print("Erro: point_of_interaction não encontrado na resposta")
#             print(f"Resposta completa: {json.dumps(payment, indent=2)}")
#             return jsonify({
#                 'success': False,
#                 'message': 'Dados do PIX não disponíveis'
#             }), 500
            
#         if "transaction_data" not in payment["point_of_interaction"]:
#             print("Erro: transaction_data não encontrado em point_of_interaction")
#             return jsonify({
#                 'success': False,
#                 'message': 'Dados do QR code não disponíveis'
#             }), 500

#         # Extract QR code data
#         qr_code = payment['point_of_interaction']['transaction_data'].get('qr_code', '')
#         qr_code_base64 = payment['point_of_interaction']['transaction_data'].get('qr_code_base64', '')
#         payment_id = payment.get('id', '')
        
#         if not qr_code or not qr_code_base64 or not payment_id:
#             print("Erro: Dados do PIX incompletos")
#             return jsonify({
#                 'success': False,
#                 'message': 'Dados do PIX incompletos'
#             }), 500

#         # Success response
#         return jsonify({
#             'success': True,
#             'qr_code': qr_code,
#             'qr_code_base64': qr_code_base64,
#             'payment_id': payment_id
#         })

#     except Exception as e:
#         print(f"=== ERRO CRÍTICO: ===")
#         print(f"Tipo do erro: {type(e)}")
#         print(f"Mensagem de erro: {str(e)}")
#         print(f"Stack trace:")
#         import traceback
#         traceback.print_exc()
        
#         return jsonify({
#             'success': False,
#             'message': f'Erro ao gerar PIX: {str(e)}'
#         }), 500


####### GERAR PIX COM WEBHOOK SUPORTE #############################

@app.route('/gerar-pix', methods=['POST'])
def gerar_pix():
    try:
        data = request.get_json()
        print(f"Raw data received: {data}")
        
        # More robust parsing with better error handling
        try:
            valor_total = round(float(data.get('valor_total', 0)), 2)
            valor_atual = round(float(data.get('valor_atual', 0)), 2)
            valor_taxa = round(float(data.get('valor_taxa', 0)), 2)
        except (ValueError, TypeError) as e:
            print(f"Error parsing values: {str(e)}")
            print(f"valor_total: {data.get('valor_total')}, type: {type(data.get('valor_total'))}")
            print(f"valor_atual: {data.get('valor_atual')}, type: {type(data.get('valor_atual'))}")
            print(f"valor_taxa: {data.get('valor_taxa')}, type: {type(data.get('valor_taxa'))}")
            
            # Try to convert from string with comma to float
            try:
                valor_total = round(float(str(data.get('valor_total', '0')).replace(',', '.')), 2)
                valor_atual = round(float(str(data.get('valor_atual', '0')).replace(',', '.')), 2)
                valor_taxa = round(float(str(data.get('valor_taxa', '0')).replace(',', '.')), 2)
                print(f"After conversion: valor_total={valor_total}, valor_atual={valor_atual}, valor_taxa={valor_taxa}")
            except Exception as conversion_error:
                print(f"Conversion attempt failed: {str(conversion_error)}")
                return jsonify({
                    'success': False,
                    'message': 'Erro ao processar valores. Verifique se os valores são numéricos válidos.'
                }), 400
        
        # Store in session
        session['valorTotal'] = valor_total
        session['valorAtual'] = valor_atual
        session['valorTaxa'] = valor_taxa
        session['formaPagto'] = 'PIX'
        
        # Validate minimum transaction amount
        if valor_total < 1:
            return jsonify({
                'success': False,
                'message': 'Valor mínimo da transação deve ser maior que R$ 1,00'
            }), 400
        
        print("=== DEBUG: Iniciando geração do PIX ===")
        print(f"Valor total processado: {valor_total}")
        print(f"Valor atual: {valor_atual}")
        print(f"Valor taxa: {valor_taxa}")
        
        # Get payer info and validate it's present
        email = session.get('user_email')
        nome_completo = session.get('user_name', '')
        
        # Fallback to data from request if session is empty
        if not email:
            email = data.get('email')
            print(f"Email not found in session, using from request: {email}")
        
        if not nome_completo:
            nome_completo = data.get('nome', '')
            print(f"Nome not found in session, using from request: {nome_completo}")
            
        nome_parts = nome_completo.split() if nome_completo else ['', '']
        
        cpf = session.get('user_cpf')
        if not cpf:
            cpf = data.get('cpf')
            print(f"CPF not found in session, using from request: {cpf}")
            
        # NOVO: Obter ID do evento
        id_evento = data.get('id_evento')
        if not id_evento:
            id_evento = session.get('id_evento')
        
        print(f"ID do evento: {id_evento}")

        # NOVO: Obter ID do evento
        evento_titulo = data.get('titulo')
        if not evento_titulo:
            evento_titulo = session.get('titulo')

        print(f"TITULO: {evento_titulo}")
            
        # Validate required fields
        if not email:
            return jsonify({
                'success': False,
                'message': 'Email do pagador é obrigatório'
            }), 400
            
        if not cpf:
            return jsonify({
                'success': False,
                'message': 'CPF do pagador é obrigatório'
            }), 400
            
        if not id_evento:
            return jsonify({
                'success': False,
                'message': 'ID do evento é obrigatório'
            }), 400
            
        # Clean CPF format
        cpf_cleaned = re.sub(r'\D', '', cpf) if cpf else ""
        session['CPF'] = cpf_cleaned

        print(f"Dados do pagador finais:")
        print(f"- Email: {email}")
        print(f"- Nome: {nome_completo}")
        print(f"- CPF: {cpf_cleaned}")
        print(f"- ID Evento: {id_evento}")

        # Try to call email function safely
        try:
            fn_email(email)
        except Exception as email_error:
            print(f"Warning: Error in fn_email: {str(email_error)}")
            # Continue processing even if email function fails

        # CORREÇÃO IMPORTANTE: Generate external_reference with event and CPF info
        import time
        external_reference = f"evento_{id_evento}_cpf_{cpf_cleaned}_timestamp_{int(time.time())}"
        print(f"External reference criado: {external_reference}")
		
        # CORREÇÃO: Melhorar preference_data
        preference_data = {
            "items": [{
                "id": f"ECM_RUN_EVENTO_{id_evento}",
                "title": "ECM RUN - Inscrição",
                "description": f"Inscrição para evento {id_evento}",
                "category_id": "sports_tickets",
                "quantity": 1,
                "unit_price": valor_total
            }],
            "statement_descriptor": "ECMRUM_INSCRICAO",
            "external_reference": external_reference,
            "notification_url": "https://ecmrun.com.br/webhook",
            # NOVO: Adicionar back_urls para melhor controle
            "back_urls": {
                "success": f"https://ecmrun.com.br/comprovante/",
                "failure": f"https://ecmrun.com.br/pagamento-falhou",
                "pending": f"https://ecmrun.com.br/pagamento-pendente"
            },
            "auto_return": "approved"
        }
        
        try:
            preference_result = sdk.preference().create(preference_data)
            print(f"Preference criada: {preference_result}")
        except Exception as pref_error:
            print(f"Erro ao criar preference: {str(pref_error)}")
            # Continue mesmo se a preference falhar

		# Calcular data de expiração
		# expiration_date = datetime.now() + timedelta(hours=1)
		# formatted_expiration = expiration_date.strftime('%Y-%m-%dT%H:%M:%S-03:00')
		
        # CORREÇÃO: Melhorar payment_data com mais informações
        payment_data = {
            "transaction_amount": float(valor_total),
            "description": f"ECM RUN - Inscrição Evento {id_evento}",
            "payment_method_id": "pix",
            "payer": {
                "email": email,
                "first_name": nome_parts[0] if nome_parts else "",
                "last_name": " ".join(nome_parts[1:]) if len(nome_parts) > 1 else "",
                "identification": {
                    "type": "CPF",
                    "number": cpf_cleaned
                }   
            },
            "notification_url": "https://ecmrun.com.br/webhook",
            "external_reference": external_reference,
            # NOVO: Adicionar informações adicionais
            "additional_info": {
                "items": [{
                    "id": f"ECM_RUN_EVENTO_{id_evento}",
                    "title": "Inscrição de Evento",
                    "description": f"Inscrição para evento {id_evento}",
                    "category_id": "SPORTS_EVENT",
                    "quantity": 1,
                    "unit_price": valor_atual
                }],
                "payer": {
                    "first_name": nome_parts[0] if nome_parts else "",
                    "last_name": " ".join(nome_parts[1:]) if len(nome_parts) > 1 else "",
                    "registration_date": datetime.now().isoformat()
                },
                "ip_address": request.remote_addr if hasattr(request, 'remote_addr') else "127.0.0.1"
            }
        }


        print("Dados do pagamento preparados:")
        print(json.dumps(payment_data, indent=2))

        # Create payment in Mercado Pago
        print("Enviando requisição para o Mercado Pago...")
        
        try:
            payment_response = sdk.payment().create(payment_data)
        except Exception as mp_error:
            print(f"Erro na comunicação com Mercado Pago: {str(mp_error)}")
            return jsonify({
                'success': False,
                'message': f'Erro na comunicação com o gateway de pagamento: {str(mp_error)}'
            }), 500
        
        print("Resposta do Mercado Pago recebida")
        
        # Validate response structure
        if not payment_response:
            print("Erro: Resposta vazia do Mercado Pago")
            return jsonify({
                'success': False,
                'message': 'Resposta vazia do gateway de pagamento'
            }), 500
            
        if "response" not in payment_response:
            print(f"Erro: Formato de resposta inesperado: {payment_response}")
            return jsonify({
                'success': False,
                'message': 'Formato de resposta inesperado do gateway de pagamento'
            }), 500

        payment = payment_response["response"]
        
        # Check for error in response
        if "error" in payment:
            print(f"Erro retornado pelo Mercado Pago: {payment}")
            return jsonify({
                'success': False,
                'message': f'Erro do gateway de pagamento: {payment.get("message", "Erro desconhecido")}'
            }), 400
        
        # Check for QR code data
        if "point_of_interaction" not in payment:
            print("Erro: point_of_interaction não encontrado na resposta")
            print(f"Resposta completa: {json.dumps(payment, indent=2)}")
            return jsonify({
                'success': False,
                'message': 'Dados do PIX não disponíveis'
            }), 500
            
        if "transaction_data" not in payment["point_of_interaction"]:
            print("Erro: transaction_data não encontrado em point_of_interaction")
            return jsonify({
                'success': False,
                'message': 'Dados do QR code não disponíveis'
            }), 500

        # Extract QR code data
        qr_code = payment['point_of_interaction']['transaction_data'].get('qr_code', '')
        qr_code_base64 = payment['point_of_interaction']['transaction_data'].get('qr_code_base64', '')
        payment_id = payment.get('id', '')
        
        if not qr_code or not qr_code_base64 or not payment_id:
            print("Erro: Dados do PIX incompletos")
            return jsonify({
                'success': False,
                'message': 'Dados do PIX incompletos'
            }), 500

        # # NOVO: Registrar o pagamento criado no banco (opcional, para controle)
        # try:
        #     registrar_pagamento_pendente(
        #         cpf=cpf_cleaned,
        #         id_evento=id_evento,
        #         payment_id=payment_id,
        #         valor_total=valor_total,
        #         external_reference=external_reference
        #     )
        # except Exception as db_error:
        #     print(f"Warning: Erro ao registrar pagamento no banco: {str(db_error)}")
        #     # Continue mesmo se o registro falhar

        print(f"PIX gerado com sucesso - Payment ID: {payment_id}")
        print(f"External Reference: {external_reference}")

        # Success response
        return jsonify({
            'success': True,
            'qr_code': qr_code,
            'qr_code_base64': qr_code_base64,
            'payment_id': payment_id,
            'external_reference': external_reference  # Útil para debug
        })

    except Exception as e:
        print(f"=== ERRO CRÍTICO: ===")
        print(f"Tipo do erro: {type(e)}")
        print(f"Mensagem de erro: {str(e)}")
        print(f"Stack trace:")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'message': f'Erro ao gerar PIX: {str(e)}'
        }), 500

#######################


@app.route('/recuperar-qrcode/<payment_id>')
def recuperar_qrcode(payment_id):
    try:
        print(f"=== RECUPERANDO QR CODE ===")
        print(f"Payment ID: {payment_id}")
        
        # Buscar o status no Mercado Pago
        payment_response = sdk.payment().get(payment_id)
        payment_data = payment_response["response"]
        
        print(f"Status no MP: {payment_data.get('status')}")
        
        if payment_data.get('status') in ['pending', 'in_process', 'approved']:
            # Extrair informações do QR Code
            qr_code = None
            qr_code_base64 = None
            
            # Buscar nas transações do pagamento
            if 'point_of_interaction' in payment_data:
                poi = payment_data['point_of_interaction']
                if 'transaction_data' in poi:
                    transaction_data = poi['transaction_data']
                    if 'qr_code' in transaction_data:
                        qr_code = transaction_data['qr_code']
                    if 'qr_code_base64' in transaction_data:
                        qr_code_base64 = transaction_data['qr_code_base64']
            
            if qr_code and qr_code_base64:
                print("QR Code encontrado e recuperado com sucesso")
                return jsonify({
                    'success': True,
                    'qr_code': qr_code,
                    'qr_code_base64': qr_code_base64,
                    'status': payment_data.get('status')
                })
            else:
                print("QR Code não encontrado nos dados do pagamento")
                return jsonify({
                    'success': False,
                    'message': 'QR Code não disponível para este pagamento'
                })
        else:
            print(f"Status do pagamento não permite recuperação: {payment_data.get('status')}")
            return jsonify({
                'success': False,
                'message': f'Pagamento com status: {payment_data.get("status")}'
            })
            
    except Exception as e:
        print(f"ERRO ao recuperar QR Code: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/verificar-pagamento/<payment_id>')
def verificar_pagamento(payment_id):
    try:
        print(f"=== VERIFICAÇÃO DE PAGAMENTO INICIADA ===")
        print(f"Payment ID recebido: {payment_id}")
        
        # Buscar o status diretamente do Mercado Pago
        payment_response = sdk.payment().get(payment_id)
        payment = payment_response["response"]

        print(f"Status do pagamento no MP: {payment['status']}")
        print(f"Dados completos do pagamento: {payment}")
        
        # CORREÇÃO: Usar total_paid_amount para pagamentos parcelados
        # Valor que o cliente efetivamente pagou (inclui juros de parcelamento)
        valor_total_pago = float(payment.get("total_paid_amount", 0))
        
        # Se total_paid_amount não estiver disponível, usar transaction_amount como fallback
        if valor_total_pago == 0:
            valor_total_pago = float(payment.get("transaction_amount", 0))
        
        valor_original_transacao = float(payment.get("transaction_amount", 0))
        
        print(f"Valor original da transação: R$ {valor_original_transacao:.2f}")
        print(f"Valor total pago pelo cliente: R$ {valor_total_pago:.2f}")
        
        # Verificar se foi parcelado
        installments = payment.get("installments", 1)
        if installments > 1:
            print(f"Pagamento parcelado em {installments}x")
            if "installment_amount" in payment:
                print(f"Valor de cada parcela: R$ {payment['installment_amount']:.2f}")
        else:
            print("Pagamento à vista")
        
        # NOVA FUNCIONALIDADE: Extrair valores de taxa e líquido
        valor_taxa_mp = 0.0
        valor_liquido = 0.0
        
        # Calcular taxa total do Mercado Pago
        if payment.get("fee_details"):
            for fee in payment["fee_details"]:
                valor_taxa_mp += float(fee.get("amount", 0))
            
            print(f"Taxas aplicadas pelo MP: R$ {valor_taxa_mp:.2f}")
            
            # Calcular valor líquido (valor TOTAL PAGO - taxas)
            valor_liquido = valor_total_pago - valor_taxa_mp
            
        else:
            # Se não houver fee_details, assumir que não há taxa (improvável)
            valor_liquido = valor_total_pago
            print("Nenhuma taxa encontrada nos detalhes do pagamento")
        
        print(f"Valor total pago pelo cliente: R$ {valor_total_pago:.2f}")
        print(f"Taxa total MP: R$ {valor_taxa_mp:.2f}")
        print(f"Valor líquido: R$ {valor_liquido:.2f}")
        
        if payment["status"] == "approved":
            print("Pagamento aprovado, processando...")
            
            data_e_hora_atual = datetime.now()
            fuso_horario = timezone('America/Manaus')
            data_pagamento = data_e_hora_atual.astimezone(fuso_horario)
            
            print(f"Data do pagamento: {data_pagamento}")

            # Buscar o registro pelo ID do pagamento (incluindo CPF)
            cur = mysql.connection.cursor()
            cur.execute("""
                SELECT IDEVENTO, IDINSCRICAO, STATUS, CPF, EMAIL, NOME, SOBRENOME, 
                       DTNASCIMENTO, DATANASC, CELULAR, SEXO, TEL_EMERGENCIA, 
                       CONT_EMERGENCIA, ESTADO, ID_CIDADE, IDPESSOA, VLINSCRICAO
                FROM EVENTO_INSCRICAO 
                WHERE IDPAGAMENTO = %s
            """, (payment_id,))
            existing_record = cur.fetchone()
            
            print(f"Registro encontrado: {existing_record}")

            if existing_record:
                idevento = existing_record[0]
                idinscricao = existing_record[1]
                status_atual = existing_record[2]
                cpf = existing_record[3]
                email = existing_record[4]
                nome = existing_record[5]
                sobrenome = existing_record[6]
                dt_nascimento = existing_record[7]
                data_nasc = existing_record[8]
                celular = existing_record[9]
                sexo = existing_record[10]
                tel_emergencia = existing_record[11]
                cont_emergencia = existing_record[12]
                estado = existing_record[13]
                id_cidade = existing_record[14]
                idpessoa_atual = existing_record[15]
                vl_inscricao = existing_record[16]
                
                # CORREÇÃO: Converter vl_inscricao para float para evitar erro de tipo
                vl_inscricao_float = float(vl_inscricao) if vl_inscricao is not None else 0.0
                
                print(f"ID Inscrição: {idinscricao}, Status atual: {status_atual}, CPF: {cpf}")
                print(f"Valor da inscrição: R$ {vl_inscricao_float:.2f}")
                print(f"Tipo de vl_inscricao: {type(vl_inscricao)} -> convertido para float: {type(vl_inscricao_float)}")
                
                # Verificar se já não foi processado (evitar reprocessamento)
                if status_atual != 'A':  # Se não está aprovado ainda

                    # Verificar se existe registro na tabela PESSOA com o CPF
                    print(f"Verificando se existe pessoa com CPF: {cpf}")
                    cur.execute("SELECT IDPESSOA FROM PESSOA WHERE CPF = %s", (cpf,))
                    pessoa_existente = cur.fetchone()
                    
                    idpessoa = None
                    
                    if pessoa_existente:
                        # CASO 2: Existe registro - fazer UPDATE na tabela PESSOA
                        idpessoa = pessoa_existente[0]
                        print(f"Pessoa encontrada com ID: {idpessoa}. Atualizando dados...")
                        
                        cur.execute("""
                            UPDATE PESSOA SET
                                EMAIL = %s,
                                NOME = %s,
                                SOBRENOME = %s,
                                DTNASCIMENTO = %s,
                                DATANASC = %s,
                                CELULAR = %s,
                                SEXO = %s,
                                TEL_EMERGENCIA = %s,
                                CONT_EMERGENCIA = %s,
                                ESTADO = %s,
                                ID_CIDADE = %s
                            WHERE CPF = %s
                        """, (
                            email, nome, sobrenome, dt_nascimento, data_nasc,
                            celular, sexo, tel_emergencia, cont_emergencia,
                            estado, id_cidade, cpf
                        ))
                        
                        print(f"Dados da pessoa {idpessoa} atualizados com sucesso")
                        
                    else:
                        # CASO 1: Não existe registro - fazer INSERT na tabela PESSOA
                        print("Pessoa não encontrada. Criando novo registro...")
                        
                        cur.execute("""
                            INSERT INTO PESSOA (
                                EMAIL, CPF, NOME, SOBRENOME, DATANASC, DTNASCIMENTO,
                                CELULAR, SEXO, TEL_EMERGENCIA, CONT_EMERGENCIA,
                                ESTADO, ID_CIDADE, DTCADASTRO
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            email, cpf, nome, sobrenome, data_nasc, dt_nascimento,
                            celular, sexo, tel_emergencia, cont_emergencia,
                            estado, id_cidade, data_e_hora_atual.astimezone(fuso_horario)
                        ))
                        
                        # Buscar o ID da pessoa recém-criada
                        cur.execute("SELECT IDPESSOA FROM PESSOA WHERE CPF = %s", (cpf,))
                        novo_registro = cur.fetchone()
                        
                        if novo_registro:
                            idpessoa = novo_registro[0]
                            print(f"Nova pessoa criada com ID: {idpessoa}")
                        else:
                            print("ERRO: Não foi possível recuperar o ID da pessoa criada")
                            raise Exception("Falha ao criar registro na tabela PESSOA")

                    # Gerar número de peito (pode implementar lógica específica)
                    cur.execute("""
                        SELECT COALESCE(MAX(NUPEITO), 0) + 1 as proximo_peito
                        FROM EVENTO_INSCRICAO 
                        WHERE STATUS = 'A' AND IDEVENTO = %s
                    """, (idevento,))
                    
                    resultado = cur.fetchone()
                    numero_peito = resultado[0] if resultado and resultado[0] else 1

                    # CORREÇÃO: Calcular vl_credito usando valor_total_pago (com juros)
                    # VLCREDITO = Valor total pago pelo cliente - Valor da inscrição
                    vl_credito = valor_total_pago - vl_inscricao_float

                    print("Atualizando status para aprovado, IDPESSOA e valores das taxas...")
                    print(f"Taxa MP: R$ {valor_taxa_mp:.2f}, Valor Líquido: R$ {valor_liquido:.2f}")
                    print(f"VL Crédito (lucro plataforma): R$ {vl_credito:.2f}")
                    print(f"Cálculo do lucro:")
                    print(f"R$ {valor_total_pago:.2f} (total pago) - R$ {vl_inscricao_float:.2f} (inscrição) = R$ {vl_credito:.2f} (lucro)")
                    
                    # ATUALIZAÇÃO COM OS NOVOS CAMPOS: VLPAGO e VLCREDITO
                    cur.execute("""
                        UPDATE EVENTO_INSCRICAO SET
                            DTPAGAMENTO = %s,
                            STATUS = %s,
                            NUPEITO = %s,
                            IDPESSOA = %s,
                            VLPAGO = %s,
                            VLTAXAMP = %s,
                            VLLIQUIDO = %s,
                            VLCREDITO = %s
                        WHERE IDPAGAMENTO = %s
                    """, (
                        data_pagamento,         
                        'A',  # APROVADO
                        numero_peito,
                        idpessoa,
                        valor_total_pago,       # Valor TOTAL que o cliente pagou (com juros)
                        valor_taxa_mp,          # Valor da taxa do Mercado Pago
                        valor_liquido,          # Valor líquido (total pago - taxas)
                        vl_credito,             # Lucro da plataforma (valor pago - valor inscrição)
                        payment_id
                    ))
                    
                    linhas_afetadas = cur.rowcount
                    mysql.connection.commit()
                    
                    print(f"Update executado. Linhas afetadas: {linhas_afetadas}")
                    print(f"Pagamento {payment_id} atualizado com sucesso")
                    print(f"IDPESSOA {idpessoa} vinculado à inscrição")
                    print(f"Taxa MP: R$ {valor_taxa_mp:.2f} - Valor Líquido: R$ {valor_liquido:.2f}")
                    print(f"Lucro Plataforma: R$ {vl_credito:.2f}")
                    
                    # Verificar se a atualização foi bem-sucedida
                    cur.execute("""
                        SELECT STATUS, DTPAGAMENTO, IDPESSOA, VLTAXAMP, VLLIQUIDO, VLPAGO, VLCREDITO 
                        FROM EVENTO_INSCRICAO 
                        WHERE IDPAGAMENTO = %s
                    """, (payment_id,))
                    verificacao = cur.fetchone()
                    print(f"Verificação pós-update: {verificacao}")
                    
                else:
                    print(f"Pagamento {payment_id} já foi processado anteriormente")
                    
                cur.close()
            else:
                print(f"ERRO: Registro não encontrado para payment_id: {payment_id}")
                
                # Buscar todos os registros para debug
                cur.execute("SELECT IDINSCRICAO, IDPAGAMENTO, STATUS FROM EVENTO_INSCRICAO ORDER BY IDINSCRICAO DESC LIMIT 10")
                todos_registros = cur.fetchall()
                print(f"Últimos 10 registros na tabela: {todos_registros}")
                
                cur.close()
                return jsonify({
                    'success': False,
                    'status': 'error',
                    'message': 'Registro não encontrado'
                }), 404
                
        print(f"=== VERIFICAÇÃO FINALIZADA ===")
        
        # RETORNO MELHORADO: incluir as informações completas de pagamento
        return jsonify({
            'success': True,
            'status': payment["status"],
            'valor_taxa_mp': round(valor_taxa_mp, 2),
            'valor_liquido': round(valor_liquido, 2),
            'valor_total_pago': round(valor_total_pago, 2),  # Valor efetivamente pago pelo cliente
            'valor_original': round(valor_original_transacao, 2),  # Valor original da transação
            'parcelado': installments > 1,
            'parcelas': installments,
            'valor_parcela': round(float(payment.get('installment_amount', 0)), 2) if installments > 1 else 0
        })
        
    except Exception as e:
        print(f"ERRO CRÍTICO ao verificar pagamento: {str(e)}")
        print(f"Tipo do erro: {type(e)}")
        import traceback
        print(f"Traceback completo: {traceback.format_exc()}")
        
        return jsonify({
            'success': False, 
            'message': str(e),
            'status': 'error'
        }), 500


@app.route('/atualiza-idpagamento/<cpf>', methods=['POST'])
def atualiza_idpagamento(cpf):
    try:
        # Obter dados do request JSON em vez de session
        data = request.json
        
        idpagamento = data.get('payment_id')
        idevento = data.get('id_evento')
        
        cur = mysql.connection.cursor()
        cur.execute("SELECT IDINSCRICAO FROM EVENTO_INSCRICAO WHERE STATUS = 'P' AND CPF = %s AND IDEVENTO = %s", (cpf, idevento))
        existing_record = cur.fetchone()
        
        if existing_record:
            cur = mysql.connection.cursor()

            cur.execute("""
                UPDATE EVENTO_INSCRICAO
                SET IDPAGAMENTO = %s
                WHERE IDINSCRICAO = %s
                """, (idpagamento, existing_record[0]))
            mysql.connection.commit()
            cur.close()
        
        return jsonify({
            'success': True,
            'status': 'inserido',
            'message': 'registrado'
        })
        
    except Exception as e:
        print(f"Erro ao lançar pré-inscrição: {str(e)}")
        # Ensure JSON is returned even on error
        return jsonify({
            'success': False, 
            'message': str(e),
            'status': 'error'
        }), 500


@app.route('/inscricao-cartao/<cpf>', methods=['POST'])
def inscricao_cartao(cpf):
    try:
        # Obter dados do request JSON em vez de session
        data = request.json
        
        idpagamento = data.get('payment_id')
        idevento = data.get('id_evento')
        
        cur = mysql.connection.cursor()
        cur.execute("SELECT IDINSCRICAO FROM EVENTO_INSCRICAO WHERE STATUS = 'P' AND CPF = %s AND IDEVENTO = %s", (cpf, idevento))
        existing_record = cur.fetchone()
        
        if existing_record:
            cur = mysql.connection.cursor()

            cur.execute("""
                UPDATE EVENTO_INSCRICAO
                SET IDPAGAMENTO = %s
                WHERE IDINSCRICAO = %s
                """, (idpagamento, existing_record[0]))
            mysql.connection.commit()
            cur.close()
        
        return jsonify({
            'success': True,
            'status': 'inserido',
            'message': 'registrado'
        })
        
    except Exception as e:
        print(f"Erro ao lançar pré-inscrição: {str(e)}")
        # Ensure JSON is returned even on error
        return jsonify({
            'success': False, 
            'message': str(e),
            'status': 'error'
        }), 500


# @app.route('/webhook', methods=['POST'])
# def webhook():
#     data = request.json
#     app.logger.info(f"Webhook received: {data}")
    
#     if data['type'] == 'payment':
#         payment_info = sdk.payment().get(data['data']['id'])
#         app.logger.info(f"Payment info: {payment_info}")
    
#     return jsonify({'status': 'ok'}), 200



# WEBHOOK COMPLETO - Processa pagamento e envia emails automaticamente
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # Log da requisição recebida
        data = request.json
        app.logger.info(f"Webhook received: {data}")
        
        # Verificar se é uma notificação de pagamento
        if data and data.get('type') == 'payment':
            payment_id = data['data']['id']
            
            app.logger.info(f"Processando webhook para payment_id: {payment_id}")
            
            # Buscar informações completas do pagamento no Mercado Pago
            payment_response = sdk.payment().get(payment_id)
            payment_info = payment_response["response"]
            
            app.logger.info(f"Status do pagamento no MP: {payment_info['status']}")
            
            # PROCESSAR PAGAMENTO APROVADO
            if payment_info['status'] == 'approved':
                # Verificar se já processamos este pagamento
                if pagamento_ja_processado_webhook(payment_id):
                    app.logger.info(f"Pagamento já processado via webhook: {payment_id}")
                    return jsonify({'status': 'already_processed'}), 200
                
                # ETAPA 1: PROCESSAR O PAGAMENTO APROVADO
                sucesso_processamento = processar_pagamento_aprovado_webhook(payment_id, payment_info)
                
                if sucesso_processamento:
                    # ETAPA 2: ENVIAR EMAILS
                    try:
                        enviar_emails_comprovante_webhook(payment_id)
                        app.logger.info(f"Pagamento processado e emails enviados com sucesso: {payment_id}")
                    except Exception as email_error:
                        app.logger.error(f"Erro ao enviar emails para payment_id {payment_id}: {str(email_error)}")
                        # Pagamento foi processado, mas email falhou - não é erro crítico
                else:
                    app.logger.error(f"Erro ao processar pagamento via webhook: {payment_id}")
            
            # PROCESSAR PAGAMENTO CANCELADO
            elif payment_info['status'] == 'cancelled':
                app.logger.info(f"Processando pagamento cancelado: {payment_id}")
                processar_pagamento_cancelado_recusado(payment_id, 'C', 'cancelado')
            
            # PROCESSAR PAGAMENTO RECUSADO/REJEITADO
            elif payment_info['status'] in ['rejected', 'refunded']:
                app.logger.info(f"Processando pagamento recusado/rejeitado: {payment_id}")
                processar_pagamento_cancelado_recusado(payment_id, 'R', 'recusado')
            
            # OUTROS STATUS (pending, in_process, etc.)
            else:
                app.logger.info(f"Status do pagamento não requer processamento: {payment_info['status']} - {payment_id}")
        
        # Sempre retornar 200 OK para o Mercado Pago
        return jsonify({'status': 'ok'}), 200
        
    except Exception as e:
        app.logger.error(f"Erro crítico no webhook: {str(e)}")
        import traceback
        app.logger.error(f"Traceback: {traceback.format_exc()}")
        # Mesmo com erro, retorna 200 para não gerar reenvios desnecessários
        return jsonify({'status': 'error', 'message': str(e)}), 200


def processar_pagamento_cancelado_recusado(payment_id, novo_status, descricao_status):
    """
    Processa pagamentos cancelados ('C') ou recusados ('R')
    """
    try:
        app.logger.info(f"=== PROCESSAMENTO DE PAGAMENTO {descricao_status.upper()} ===")
        app.logger.info(f"Payment ID: {payment_id}, Novo Status: {novo_status}")
        
        # Verificar se existe o registro no banco
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT IDINSCRICAO, STATUS, CPF, EMAIL, NOME, SOBRENOME, IDEVENTO
            FROM EVENTO_INSCRICAO 
            WHERE IDPAGAMENTO = %s
        """, (payment_id,))
        
        registro = cur.fetchone()
        
        if not registro:
            app.logger.warning(f"Registro não encontrado para payment_id {descricao_status}: {payment_id}")
            cur.close()
            return False
        
        idinscricao, status_atual, cpf, email, nome, sobrenome, idevento = registro
        
        app.logger.info(f"Registro encontrado - Inscrição: {idinscricao}, Status atual: {status_atual}")
        
        # Só atualizar se não estiver já cancelado/recusado
        if status_atual not in ['C', 'R']:
            
            # Data e hora atual para registro do cancelamento/recusa
            data_e_hora_atual = datetime.now()
            fuso_horario = timezone('America/Manaus')
            data_status = data_e_hora_atual.astimezone(fuso_horario)
            
            # Se era aprovado, precisamos liberar o número do peito
            if status_atual == 'A':
                app.logger.info(f"Pagamento era aprovado, liberando número do peito...")
                cur.execute("""
                    UPDATE EVENTO_INSCRICAO SET
                        STATUS = %s,
                        DTSTATUSCHANGE = %s,
                        NUPEITO = NULL,
                        VLPAGO = NULL,
                        VLTAXAMP = NULL,
                        VLLIQUIDO = NULL,
                        VLCREDITO = NULL
                    WHERE IDPAGAMENTO = %s
                """, (novo_status, data_status, payment_id))
            else:
                # Se era pendente, apenas mudar o status
                cur.execute("""
                    UPDATE EVENTO_INSCRICAO SET
                        STATUS = %s,
                        DTSTATUSCHANGE = %s
                    WHERE IDPAGAMENTO = %s
                """, (novo_status, data_status, payment_id))
            
            linhas_afetadas = cur.rowcount
            mysql.connection.commit()
            
            if linhas_afetadas > 0:
                app.logger.info(f"Status atualizado para '{novo_status}' - Pagamento {payment_id} {descricao_status}")
                
                # OPCIONAL: Enviar email de notificação sobre cancelamento/recusa
                try:
                    enviar_email_cancelamento(email, nome, sobrenome, payment_id, novo_status, descricao_status)
                except Exception as email_error:
                    app.logger.error(f"Erro ao enviar email de {descricao_status}: {str(email_error)}")
                
                cur.close()
                return True
            else:
                app.logger.warning(f"Nenhuma linha foi atualizada para payment_id {descricao_status}: {payment_id}")
                cur.close()
                return False
        
        else:
            app.logger.info(f"Pagamento {payment_id} já estava com status {status_atual}")
            cur.close()
            return True  # Já estava no status correto
            
    except Exception as e:
        app.logger.error(f"Erro ao processar pagamento {descricao_status}: {str(e)}")
        import traceback
        app.logger.error(f"Traceback: {traceback.format_exc()}")
        if 'cur' in locals():
            cur.close()
        return False


def enviar_email_cancelamento(email, nome, sobrenome, payment_id, status, descricao):
    """
    OPCIONAL: Envia email de notificação sobre cancelamento/recusa
    """
    try:
        nome_completo = f"{nome} {sobrenome}"
        
        if status == 'C':
            assunto = "Pagamento Cancelado - Inscrição"
            mensagem = f"""
            Olá {nome_completo},

            Informamos que o pagamento da sua inscrição foi cancelado.

            ID do Pagamento: {payment_id}
            
            Se você deseja realizar uma nova tentativa de pagamento, 
            acesse novamente o link de inscrição.

            Atenciosamente,
            Equipe de Eventos
            """
        else:  # status == 'R'
            assunto = "Pagamento Recusado - Inscrição"
            mensagem = f"""
            Olá {nome_completo},

            Informamos que o pagamento da sua inscrição foi recusado.

            ID do Pagamento: {payment_id}
            
            Isso pode acontecer por diversos motivos como:
            - Dados do cartão incorretos
            - Limite insuficiente
            - Problemas na operadora

            Para realizar uma nova tentativa, acesse novamente o link de inscrição.

            Atenciosamente,
            Equipe de Eventos
            """
        
        # Aqui você pode implementar o envio do email usando sua função existente
        # send_custom_email(email, assunto, mensagem)
        
        app.logger.info(f"Email de {descricao} enviado para: {email}")
        
    except Exception as e:
        app.logger.error(f"Erro ao enviar email de {descricao}: {str(e)}")


def pagamento_ja_processado_webhook(payment_id):
    """
    Verifica se o pagamento já foi processado para evitar duplicações
    (Mantém apenas para pagamentos aprovados)
    """
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT STATUS FROM EVENTO_INSCRICAO 
            WHERE IDPAGAMENTO = %s AND STATUS = 'A'
        """, (payment_id,))
        
        resultado = cur.fetchone()
        cur.close()
        
        return resultado is not None
        
    except Exception as e:
        app.logger.error(f"Erro ao verificar pagamento processado: {str(e)}")
        return False
    

def processar_pagamento_aprovado_webhook(payment_id, payment_info):
    """
    Processa o pagamento aprovado - CÓDIGO DA ROTA verificar-pagamento
    Retorna True se processado com sucesso, False caso contrário
    """
    try:
        app.logger.info(f"=== PROCESSAMENTO VIA WEBHOOK INICIADO ===")
        app.logger.info(f"Payment ID: {payment_id}")
        
        # CALCULAR VALORES E TAXAS (mesmo código da rota original)
        valor_taxa_mp = 0.0
        valor_liquido = 0.0
        valor_total_transacao = float(payment_info.get("transaction_amount", 0))
        
        if payment_info.get("fee_details"):
            for fee in payment_info["fee_details"]:
                valor_taxa_mp += float(fee.get("amount", 0))
            valor_liquido = valor_total_transacao - valor_taxa_mp
        else:
            valor_liquido = valor_total_transacao
        
        app.logger.info(f"Valores calculados - Total: R$ {valor_total_transacao:.2f}, Taxa MP: R$ {valor_taxa_mp:.2f}, Líquido: R$ {valor_liquido:.2f}")
        
        # BUSCAR REGISTRO NO BANCO
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT IDEVENTO, IDINSCRICAO, STATUS, CPF, EMAIL, NOME, SOBRENOME, 
                   DTNASCIMENTO, DATANASC, CELULAR, SEXO, TEL_EMERGENCIA, 
                   CONT_EMERGENCIA, ESTADO, ID_CIDADE, IDPESSOA, VLINSCRICAO
            FROM EVENTO_INSCRICAO 
            WHERE IDPAGAMENTO = %s
        """, (payment_id,))
        
        existing_record = cur.fetchone()
        
        if not existing_record:
            app.logger.error(f"Registro não encontrado para payment_id: {payment_id}")
            cur.close()
            return False
        
        # EXTRAIR DADOS DO REGISTRO
        (idevento, idinscricao, status_atual, cpf, email, nome, sobrenome, 
         dt_nascimento, data_nasc, celular, sexo, tel_emergencia, 
         cont_emergencia, estado, id_cidade, idpessoa_atual, vl_inscricao) = existing_record
        
        vl_inscricao_float = float(vl_inscricao) if vl_inscricao is not None else 0.0
        
        app.logger.info(f"Processando inscrição {idinscricao} - CPF: {cpf} - Status atual: {status_atual}")
        
        # SÓ PROCESSAR SE NÃO ESTIVER APROVADO
        if status_atual != 'A':
            
            # DATA E HORA ATUAL
            data_e_hora_atual = datetime.now()
            fuso_horario = timezone('America/Manaus')
            data_pagamento = data_e_hora_atual.astimezone(fuso_horario)
            
            # VERIFICAR/CRIAR PESSOA
            idpessoa = processar_pessoa_webhook(cur, cpf, email, nome, sobrenome, 
                                              dt_nascimento, data_nasc, celular, sexo, 
                                              tel_emergencia, cont_emergencia, estado, 
                                              id_cidade, data_e_hora_atual, fuso_horario)
            
            if not idpessoa:
                app.logger.error(f"Erro ao processar pessoa para CPF: {cpf}")
                cur.close()
                return False
            
            # GERAR NÚMERO DO PEITO
            cur.execute("""
                SELECT COALESCE(MAX(NUPEITO), 0) + 1 as proximo_peito
                FROM EVENTO_INSCRICAO 
                WHERE STATUS = 'A' AND IDEVENTO = %s
            """, (idevento,))
            
            resultado = cur.fetchone()
            numero_peito = resultado[0] if resultado and resultado[0] else 1
            
            # CALCULAR CRÉDITO DA PLATAFORMA
            vl_credito = valor_liquido - vl_inscricao_float
            
            app.logger.info(f"Atualizando inscrição - Número peito: {numero_peito}, VL Crédito: R$ {vl_credito:.2f}")
            
            # ATUALIZAR INSCRIÇÃO PARA APROVADA
            cur.execute("""
                UPDATE EVENTO_INSCRICAO SET
                    DTPAGAMENTO = %s,
                    STATUS = %s,
                    NUPEITO = %s,
                    IDPESSOA = %s,
                    VLPAGO = %s,
                    VLTAXAMP = %s,
                    VLLIQUIDO = %s,
                    VLCREDITO = %s
                WHERE IDPAGAMENTO = %s
            """, (
                data_pagamento,         
                'A',  # APROVADO
                numero_peito,
                idpessoa,
                valor_total_transacao,
                valor_taxa_mp,
                valor_liquido,
                vl_credito,
                payment_id
            ))
            
            linhas_afetadas = cur.rowcount
            mysql.connection.commit()
            
            app.logger.info(f"Inscrição atualizada via webhook - Linhas afetadas: {linhas_afetadas}")
            
            if linhas_afetadas > 0:
                cur.close()
                return True
            else:
                app.logger.error(f"Nenhuma linha foi atualizada para payment_id: {payment_id}")
                cur.close()
                return False
        
        else:
            app.logger.info(f"Pagamento {payment_id} já estava aprovado")
            cur.close()
            return True  # Já processado, mas não é erro
            
    except Exception as e:
        app.logger.error(f"Erro ao processar pagamento via webhook: {str(e)}")
        import traceback
        app.logger.error(f"Traceback: {traceback.format_exc()}")
        if 'cur' in locals():
            cur.close()
        return False


def processar_pessoa_webhook(cur, cpf, email, nome, sobrenome, dt_nascimento, 
                           data_nasc, celular, sexo, tel_emergencia, cont_emergencia, 
                           estado, id_cidade, data_e_hora_atual, fuso_horario):
    """
    Processa a criação/atualização da pessoa - MESMO CÓDIGO DA ROTA ORIGINAL
    """
    try:
        # Verificar se existe registro na tabela PESSOA com o CPF
        cur.execute("SELECT IDPESSOA FROM PESSOA WHERE CPF = %s", (cpf,))
        pessoa_existente = cur.fetchone()
        
        if pessoa_existente:
            # PESSOA EXISTE - ATUALIZAR
            idpessoa = pessoa_existente[0]
            app.logger.info(f"Pessoa encontrada com ID: {idpessoa}. Atualizando dados via webhook...")
            
            cur.execute("""
                UPDATE PESSOA SET
                    EMAIL = %s,
                    NOME = %s,
                    SOBRENOME = %s,
                    DTNASCIMENTO = %s,
                    DATANASC = %s,
                    CELULAR = %s,
                    SEXO = %s,
                    TEL_EMERGENCIA = %s,
                    CONT_EMERGENCIA = %s,
                    ESTADO = %s,
                    ID_CIDADE = %s
                WHERE CPF = %s
            """, (
                email, nome, sobrenome, dt_nascimento, data_nasc,
                celular, sexo, tel_emergencia, cont_emergencia,
                estado, id_cidade, cpf
            ))
            
        else:
            # PESSOA NÃO EXISTE - CRIAR
            app.logger.info("Pessoa não encontrada. Criando novo registro via webhook...")
            
            cur.execute("""
                INSERT INTO PESSOA (
                    EMAIL, CPF, NOME, SOBRENOME, DATANASC, DTNASCIMENTO,
                    CELULAR, SEXO, TEL_EMERGENCIA, CONT_EMERGENCIA,
                    ESTADO, ID_CIDADE, DTCADASTRO
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                email, cpf, nome, sobrenome, data_nasc, dt_nascimento,
                celular, sexo, tel_emergencia, cont_emergencia,
                estado, id_cidade, data_e_hora_atual.astimezone(fuso_horario)
            ))
            
            # Buscar o ID da pessoa recém-criada
            cur.execute("SELECT IDPESSOA FROM PESSOA WHERE CPF = %s", (cpf,))
            novo_registro = cur.fetchone()
            
            if novo_registro:
                idpessoa = novo_registro[0]
                app.logger.info(f"Nova pessoa criada via webhook com ID: {idpessoa}")
            else:
                app.logger.error("ERRO: Não foi possível recuperar o ID da pessoa criada via webhook")
                return None
        
        return idpessoa
        
    except Exception as e:
        app.logger.error(f"Erro ao processar pessoa via webhook: {str(e)}")
        return None


def enviar_emails_comprovante_webhook(payment_id):
    """
    Envia os emails de comprovante - CÓDIGO ADAPTADO DA ROTA comprovante
    """
    try:
        app.logger.info(f"Enviando emails para payment_id: {payment_id}")
        
        # BUSCAR DADOS DO COMPROVANTE (mesmo SQL da rota original)
        cur = mysql.connection.cursor()
        
        cur.execute('''
            SELECT ei.DTPAGAMENTO, e.TITULO, e.ENDERECO, 
                e.DATAINICIO, e.DATAFIM, e.HRINICIO,
                CONCAT(ei.NOME, ' ', ei.SOBRENOME) AS NOME_COMPLETO, 
                CASE WHEN i.KM = 0
                    THEN i.MODALIDADE
                    ELSE CONCAT(i.KM, ' KM') 
                END AS KM_DESCRICAO, 
                ei.VLINSCRICAO, ei.VLTOTAL, ei.FORMAPGTO, 
                ei.IDPAGAMENTO, ei.FLEMAIL, ei.IDINSCRICAO, 
                e.OBS, ei.CPF, ei.DTNASCIMENTO 
            FROM EVENTO_INSCRICAO ei
            INNER JOIN EVENTO1 e ON e.IDEVENTO = ei.IDEVENTO
            INNER JOIN EVENTO_ITEM i ON i.IDITEM = ei.IDITEMEVENTO
            WHERE ei.STATUS = 'A' 
            AND ei.IDPAGAMENTO = %s 
        ''', (payment_id,))
        
        receipt_data = cur.fetchone()
        
        if not receipt_data:
            app.logger.error(f"Dados do comprovante não encontrados para payment_id: {payment_id}")
            cur.close()
            return False
        
        # PROCESSAR DADOS DO COMPROVANTE (mesmo código da rota original)
        data_pagamento = receipt_data[0]
        data_inicio = receipt_data[3]
        data_fim = receipt_data[4]
        hr_inicio = receipt_data[5]
        
        # Formatar data de pagamento
        if isinstance(data_pagamento, datetime):
            data_formatada = data_pagamento.strftime('%d/%m/%Y %H:%M:%S')
        else:
            data_formatada = str(data_pagamento)
        
        # Formatar data do evento
        if isinstance(data_inicio, datetime) and isinstance(data_fim, datetime):
            if data_inicio.date() == data_fim.date():
                data_evento = f"{data_inicio.strftime('%d/%m/%Y')} {hr_inicio}"
            else:
                data_evento = f"{data_inicio.strftime('%d/%m/%Y')} {hr_inicio} - {data_fim.strftime('%d/%m/%Y')}"
        else:
            data_evento = f"{data_inicio} {hr_inicio}"

        # Estruturar os dados do comprovante
        receipt_data_dict = { 
            'data': data_formatada,
            'evento': receipt_data[1],
            'endereco': receipt_data[2],
            'dataevento': data_evento,
            'participante': receipt_data[6],
            'km': receipt_data[7],
            'valor': f'R$ {receipt_data[8]:,.2f}',
            'valortotal': f'R$ {receipt_data[9]:,.2f}',
            'formapgto': receipt_data[10],
            'inscricao': str(receipt_data[11]),
            'obs': receipt_data[14] if receipt_data[14] is not None else ''
        }
        
        flemail = receipt_data[12]
        id_inscricao = receipt_data[13]
        
        app.logger.info(f"Dados do comprovante processados - FLEMAIL: {flemail}, ID_INSCRICAO: {id_inscricao}")
        
        # ENVIAR EMAILS APENAS SE NÃO FOI ENVIADO ANTES
        if flemail == 'N':
            app.logger.info(f"Enviando emails para inscrição {id_inscricao}...")
            
            # Enviar email para o participante
            try:
                send_email(receipt_data_dict)
                app.logger.info("Email enviado para o participante com sucesso")
            except Exception as email_error:
                app.logger.error(f"Erro ao enviar email para participante: {str(email_error)}")
                # Continua mesmo se falhar
            
            # Enviar notificação para o organizador
            try:
                send_organizer_notification(receipt_data_dict)
                app.logger.info("Email enviado para o organizador com sucesso")
            except Exception as org_error:
                app.logger.error(f"Erro ao enviar email para organizador: {str(org_error)}")
                # Continua mesmo se falhar

            # MARCAR EMAIL COMO ENVIADO
            cur.execute('''
                UPDATE EVENTO_INSCRICAO SET FLEMAIL = 'S'
                WHERE IDINSCRICAO = %s
            ''', (id_inscricao,))

            mysql.connection.commit()
            app.logger.info(f"Flag FLEMAIL atualizada para 'S' na inscrição {id_inscricao}")
        
        else:
            app.logger.info(f"Emails já foram enviados anteriormente para inscrição {id_inscricao}")
        
        cur.close()
        return True
        
    except Exception as e:
        app.logger.error(f"Erro ao enviar emails via webhook: {str(e)}")
        import traceback
        app.logger.error(f"Traceback: {traceback.format_exc()}")
        return False


# ROTA PARA MONITORAR WEBHOOKS (opcional - para debugging)
@app.route('/webhook-logs')
def webhook_logs():
    """
    Página para visualizar os últimos pagamentos processados via webhook
    """
    try:
        cur = mysql.connection.cursor()
        
        # Buscar últimos pagamentos aprovados
        cur.execute("""
            SELECT 
                ei.IDPAGAMENTO,
                ei.CPF,
                CONCAT(ei.NOME, ' ', ei.SOBRENOME) as NOME_COMPLETO,
                e.TITULO as EVENTO,
                ei.DTPAGAMENTO,
                ei.VLTOTAL,
                ei.FLEMAIL,
                ei.STATUS
            FROM EVENTO_INSCRICAO ei
            INNER JOIN EVENTO1 e ON e.IDEVENTO = ei.IDEVENTO
            WHERE ei.STATUS = 'A' 
            AND ei.DTPAGAMENTO IS NOT NULL
            ORDER BY ei.DTPAGAMENTO DESC 
            LIMIT 50
        """)
        
        payments = cur.fetchall()
        cur.close()
        
        return render_template('webhook_logs.html', payments=payments)
        
    except Exception as e:
        app.logger.error(f"Erro ao buscar logs: {str(e)}")
        return f"Erro ao carregar logs: {str(e)}", 500


# ROTA PARA TESTAR O WEBHOOK MANUALMENTE (só para desenvolvimento)
@app.route('/test-webhook', methods=['POST'])
def test_webhook():
    """
    Rota para testar o processamento do webhook em desenvolvimento
    Uso: POST /test-webhook com {"payment_id": "123456789"}
    """
    if app.debug:  # Só funciona em modo debug
        try:
            data = request.get_json()
            payment_id = data.get('payment_id')
            
            if not payment_id:
                return jsonify({'error': 'payment_id é obrigatório'}), 400
            
            # Simular dados do webhook
            test_data = {
                "type": "payment",
                "data": {
                    "id": payment_id
                }
            }
            
            app.logger.info(f"Testando webhook para payment_id: {payment_id}")
            
            # Processar usando a mesma lógica do webhook real
            payment_response = sdk.payment().get(payment_id)
            payment_info = payment_response["response"]
            
            if payment_info['status'] == 'approved':
                sucesso = processar_pagamento_aprovado_webhook(payment_id, payment_info)
                
                if sucesso:
                    enviar_emails_comprovante_webhook(payment_id)
                    return jsonify({
                        'success': True, 
                        'message': 'Pagamento processado e emails enviados com sucesso'
                    })
                else:
                    return jsonify({
                        'success': False, 
                        'message': 'Erro ao processar pagamento'
                    }), 500
            else:
                return jsonify({
                    'success': False, 
                    'message': f'Pagamento não está aprovado. Status: {payment_info["status"]}'
                }), 400
                
        except Exception as e:
            app.logger.error(f"Erro no teste do webhook: {str(e)}")
            return jsonify({'error': str(e)}), 500
    else:
        return jsonify({'error': 'Disponível apenas em modo debug'}), 403


# FUNÇÃO PARA VERIFICAR STATUS DO WEBHOOK (útil para monitoramento)
@app.route('/webhook-status/<payment_id>')
def webhook_status(payment_id):
    """
    Verifica se um pagamento foi processado via webhook
    """
    try:
        cur = mysql.connection.cursor()
        
        cur.execute("""
            SELECT 
                STATUS,
                DTPAGAMENTO,
                FLEMAIL,
                VLTOTAL,
                CONCAT(NOME, ' ', SOBRENOME) as NOME
            FROM EVENTO_INSCRICAO 
            WHERE IDPAGAMENTO = %s
        """, (payment_id,))
        
        resultado = cur.fetchone()
        cur.close()
        
        if resultado:
            status, dt_pagamento, flemail, vl_total, nome = resultado
            
            return jsonify({
                'found': True,
                'payment_id': payment_id,
                'status': status,
                'dt_pagamento': dt_pagamento.isoformat() if dt_pagamento else None,
                'email_enviado': flemail == 'S',
                'valor_total': float(vl_total) if vl_total else 0,
                'nome': nome,
                'processado_webhook': status == 'A' and dt_pagamento is not None
            })
        else:
            return jsonify({
                'found': False,
                'payment_id': payment_id,
                'message': 'Pagamento não encontrado'
            })
            
    except Exception as e:
        app.logger.error(f"Erro ao verificar status do webhook: {str(e)}")
        return jsonify({'error': str(e)}), 500


# FUNÇÃO PARA REPROCESSAR UM PAGAMENTO (caso algo dê errado)
@app.route('/reprocessar-pagamento/<payment_id>', methods=['POST'])
def reprocessar_pagamento(payment_id):
    """
    Reprocessa um pagamento específico (útil se o webhook falhar)
    """
    try:
        app.logger.info(f"Reprocessamento manual solicitado para payment_id: {payment_id}")
        
        # Buscar informações do pagamento no Mercado Pago
        payment_response = sdk.payment().get(payment_id)
        payment_info = payment_response["response"]
        
        if payment_info['status'] != 'approved':
            return jsonify({
                'success': False,
                'message': f'Pagamento não está aprovado. Status atual: {payment_info["status"]}'
            }), 400
        
        # Verificar se já foi processado
        if pagamento_ja_processado_webhook(payment_id):
            # Se já foi processado, só reenvia os emails se necessário
            try:
                enviar_emails_comprovante_webhook(payment_id)
                return jsonify({
                    'success': True,
                    'message': 'Pagamento já estava processado. Emails reenviados com sucesso.'
                })
            except Exception as email_error:
                return jsonify({
                    'success': False,
                    'message': f'Pagamento já processado, mas erro ao reenviar emails: {str(email_error)}'
                }), 500
        
        # Processar pagamento
        sucesso_processamento = processar_pagamento_aprovado_webhook(payment_id, payment_info)
        
        if sucesso_processamento:
            # Enviar emails
            try:
                enviar_emails_comprovante_webhook(payment_id)
                return jsonify({
                    'success': True,
                    'message': 'Pagamento reprocessado e emails enviados com sucesso'
                })
            except Exception as email_error:
                return jsonify({
                    'success': True,
                    'message': f'Pagamento processado com sucesso, mas erro ao enviar emails: {str(email_error)}'
                })
        else:
            return jsonify({
                'success': False,
                'message': 'Erro ao reprocessar pagamento'
            }), 500
            
    except Exception as e:
        app.logger.error(f"Erro no reprocessamento: {str(e)}")
        return jsonify({
            'success': False, 
            'message': f'Erro no reprocessamento: {str(e)}'
        }), 500


######### fim da implementação do webhook #####################################

# @app.route('/criar_preferencia', methods=['POST'])
# def criar_preferencia():

#     app.logger.info("Recebendo requisição para criar preferência")
#     app.logger.debug(f"Dados recebidos: {request.get_json()}")
#     app.logger.debug(f"MP_ACCESS_TOKEN configurado: {'MP_ACCESS_TOKEN' in os.environ}")

#     try:
#         data = request.get_json()
        
#         # Log dos dados recebidos
#         print("Dados recebidos:", data)
        
#         # Get values from localStorage (sent in request)
#         valor_total = float(data.get('valortotal', 0))
#         valor_taxa = float(data.get('valortaxa', 0))
#         nome_completo = data.get('user_name', '')
        
#         # Split full name into first and last name
#         nome_parts = nome_completo.split(' ', 1)
#         first_name = nome_parts[0]
#         last_name = nome_parts[1] if len(nome_parts) > 1 else ''
        
#         preco_final = valor_total
        
#         print("Preço final calculado:", preco_final)
        
#         # Configurar URLs de retorno
#         base_url = request.url_root.rstrip('/')  # Remove trailing slash if present

#         back_urls = {
#             "success": f"{base_url}/aprovado",
#             "failure": f"{base_url}/negado",
#             "pending": f"{base_url}/negado"
#         }

#         preference_data = {
#             "items": [
#                 {
#                     "id": "ECM RUN TICHETS",
#                     "title": "Inscrição de Corrida",
#                     "quantity": 1,
#                     "unit_price": float(preco_final),
#                     "description": "Inscrição de Evento",
#                     "category_id": "sports_tickets"
#                 }
#             ],
#             "payer": {
#                 "first_name": first_name,
#                 "last_name": last_name,
#                 "email": data.get('user_email')
#             },
#             "payment_methods": {
#                 "excluded_payment_methods": [
#                     {"id": "bolbradesco"},
#                     {"id": "pix"}
#                 ],
#                 "excluded_payment_types": [
#                     {"id": "ticket"},
#                     {"id": "bank_transfer"}
#                 ],
#                 "installments": 12
#             },
#             "back_urls": back_urls,
#             "auto_return": "approved",
#             "statement_descriptor": "ECM RUN",
#             "external_reference": data.get('user_idatleta'),
#             "notification_url": f"{back_urls['success'].rsplit('/', 1)[0]}/webhook"
#         }
        
#         # Log da preference antes de criar
#         print("Preference data:", preference_data)
        
#         preference_response = sdk.preference().create(preference_data)
#         print("Resposta do MP:", preference_response)
        
#         if "response" not in preference_response:
#             raise Exception("Erro na resposta do Mercado Pago: " + str(preference_response))
            
#         preference = preference_response["response"]
        
#         return jsonify({
#             "id": preference["id"],
#             "init_point": preference["init_point"]
#         })
    
#     except Exception as e:
#         print("Erro detalhado:", str(e))
#         return jsonify({"error": str(e)}), 400


@app.route('/pesquisa-cupom/<int:categoria_id>/<cpf>/<cupom>')
def pesquisa_cupom(categoria_id, cpf, cupom):
    try:
        print(f"Recebido pedido de validação - Categoria: {categoria_id}, CPF: {cpf}, Cupom: {cupom}")
        
        cur = mysql.connection.cursor()
        query = "SELECT IDCUPOM, IDPAGAMENTO FROM ecmrun.CUPOM WHERE UTILIZADO = 'N' AND IDMODALIDADE = %s AND CPF = %s AND CUPOM = %s"
        
        print(f"Executando query: {query} com parâmetros: {(categoria_id, cpf, cupom)}")
        
        cur.execute(query, (categoria_id, cpf, cupom))
        result = cur.fetchone()
        
        print(f"Resultado da query: {result}")
        
        cur.close()

        if result:
            return jsonify({
                'success': True,
                'idcupom': result[0],
                'idpagamento': result[1]
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Número do cupom não encontrado ou não vinculado a este CPF e/ou Modalidade selecionada. Verifique e tente novamente.'
            })
    except Exception as e:
        print(f"Erro na validação do cupom: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

    

@app.route('/verificar_senha', methods=['POST'])
def verificar_senha():
    senha = request.form.get('senha')
    senha_adm = os.getenv('SENHA_ADM')
    
    if senha == senha_adm:
        # Criar uma autenticação temporária para esta requisição apenas
        session['authenticated'] = True
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': 'Senha incorreta'})

@app.route('/logout')
def logout():
    session.pop('authenticated', None)
    return redirect(url_for('desafio200k'))


# Rota para exibir a página de cadastro
@app.route('/apoio200k')
def apoio_cadastro():
    return render_template('apoio200k.html')

# API para buscar atletas
@app.route('/api/atletas')
def get_atletas():
    try:
        cursor = mysql.connection.cursor()
        query = """
            SELECT A.IDATLETA, CONCAT(A.NOME,' ',A.SOBRENOME) AS ATLETA
            FROM INSCRICAO I, ATLETA A
            WHERE A.IDATLETA = I.IDATLETA
            AND I.IDEVENTO = 1
            ORDER BY CONCAT(A.NOME,' ',A.SOBRENOME)
        """
        cursor.execute(query)
        atletas = cursor.fetchall()
        cursor.close()
        
        # Converter para lista de dicionários
        atletas_list = []
        for atleta in atletas:
            atletas_list.append({
                'IDATLETA': atleta[0],
                'ATLETA': atleta[1]
            })
        
        return jsonify(atletas_list)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API para cadastrar apoio
@app.route('/api/cadastrar-apoio', methods=['POST'])
def cadastrar_apoio():
    try:
        data = request.get_json()
        
        # Validar dados obrigatórios (veículo e placa agora são opcionais)
        if not all([data.get('nome'), data.get('celular'), 
                   data.get('idatleta'), data.get('aceite')]):
            return jsonify({'message': 'Nome, celular, atleta e aceite são obrigatórios'}), 400
        
        # Verificar se aceite é 'S'
        if data.get('aceite') != 'S':
            return jsonify({'message': 'É necessário aceitar o regulamento'}), 400
        
        cursor = mysql.connection.cursor()
        
        # Verificar se já existe apoio com mesmo nome e celular para o mesmo atleta
        check_query = """
            SELECT COUNT(*) FROM APOIO 
            WHERE UPPER(NOME) = %s AND CELULAR = %s AND IDATLETA = %s
        """
        cursor.execute(check_query, (
            data['nome'].upper().strip(),
            data['celular'].strip(),
            data['idatleta']
        ))
        
        if cursor.fetchone()[0] > 0:
            cursor.close()
            return jsonify({'message': 'Já existe um apoio cadastrado com este nome e celular para este atleta'}), 400
        
        # Obter data e hora de Manaus
        data_e_hora_atual = datetime.now()
        fuso_horario = timezone('America/Manaus')
        data_e_hora_manaus = data_e_hora_atual.astimezone(fuso_horario)
        
        # Inserir novo apoio
        insert_query = """
            INSERT INTO APOIO (NOME, CELULAR, VEICULO, PLACA, IDATLETA, DT_CADASTRO, ACEITE)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(insert_query, (
            data['nome'].upper().strip(),
            data['celular'].strip(),
            data.get('veiculo', '').upper().strip(),
            data.get('placa', '').upper().strip(),
            data['idatleta'],
            data_e_hora_manaus,
            data['aceite']
        ))
        
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({'message': 'Apoio cadastrado com sucesso'}), 200
    
    except Exception as e:
        return jsonify({'message': f'Erro interno do servidor: {str(e)}'}), 500


# Rota para verificar senha
@app.route('/verificar_senha1', methods=['POST'])
def verificar_senha1():
    print("DEBUG: Verificando senha...")
    try:
        data = request.get_json()
        print(f"DEBUG: Dados recebidos: {data}")
        
        senha_informada = data.get('senha')
        senha_correta = os.getenv('SENHA_ACESSO')
        
        print(f"DEBUG: Senha informada: {senha_informada}")
        print(f"DEBUG: Senha do ambiente existe: {senha_correta is not None}")
                
        if senha_informada == senha_correta:
            session['autenticado'] = True
            print("DEBUG: Autenticação bem-sucedida")
            return jsonify({'success': True})
        else:
            print("DEBUG: Senha incorreta")
            return jsonify({'success': False, 'message': 'Senha incorreta'})
            
    except Exception as e:
        print(f"DEBUG: Erro na verificação da senha: {str(e)}")
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'})



# Rota para buscar modalidades por evento
@app.route('/api/modalidades1/<int:evento_id>')
def get_modalidades1(evento_id):
    print(f"DEBUG: Buscando modalidades para evento {evento_id}")
    
    if not session.get('autenticado'):
        print("DEBUG: Usuário não autenticado")
        return jsonify({'error': 'Não autenticado'}), 401
    
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT IDITEM, DESCRICAO FROM EVENTO_MODALIDADE WHERE IDEVENTO = %s", (evento_id,))
        modalidades = cursor.fetchall()
        cursor.close()
        
        print(f"DEBUG: Encontradas {len(modalidades)} modalidades")
        
        modalidades_list = []
        for modalidade in modalidades:
            modalidades_list.append({
                'IDITEM': modalidade[0],
                'DESCRICAO': modalidade[1]
            })
        
        return jsonify(modalidades_list)
        
    except Exception as e:
        print(f"DEBUG: Erro ao buscar modalidades: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/modalidades2/<int:evento_id>')
def get_modalidades2(evento_id):
    print(f"DEBUG: Buscando modalidades para evento {evento_id}")
    
    if not session.get('autenticado'):
        print("DEBUG: Usuário não autenticado")
        return jsonify({'error': 'Não autenticado'}), 401
    
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT IDITEM, DESCRICAO FROM EVENTO_MODALIDADE WHERE IDITEM <> 1 AND IDEVENTO = %s", (evento_id,))
        modalidades = cursor.fetchall()
        cursor.close()
        
        print(f"DEBUG: Encontradas {len(modalidades)} modalidades")
        
        modalidades_list = []
        for modalidade in modalidades:
            modalidades_list.append({
                'IDITEM': modalidade[0],
                'DESCRICAO': modalidade[1]
            })
        
        return jsonify(modalidades_list)
        
    except Exception as e:
        print(f"DEBUG: Erro ao buscar modalidades: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Rota para buscar inscrições por evento e modalidade
@app.route('/api/inscricoes/<int:evento_id>')
@app.route('/api/inscricoes/<int:evento_id>/<int:modalidade_id>')
def get_inscricoes(evento_id, modalidade_id=None):
    print(f"DEBUG: Buscando inscrições para evento {evento_id}, modalidade {modalidade_id}")
    
    if not session.get('autenticado'):
        print("DEBUG: Usuário não autenticado")
        return jsonify({'error': 'Não autenticado'}), 401
    
    try:
        cursor = mysql.connection.cursor()
        
        if modalidade_id:
            query = """
            SELECT CONCAT(COALESCE(I.NUPEITO, ''),' ',A.NOME,' ',A.SOBRENOME) AS ATLETA, 
                   I.CAMISETA,
                   EV.DESCRICAO,
                   I.IDINSCRICAO,
                   A.SEXO,
                   I.FLSTATUS,
                   I.NUPEITO
            FROM ATLETA A, INSCRICAO I, EVENTO_MODALIDADE EV
            WHERE 
            EV.IDITEM = I.IDITEM
            AND A.IDATLETA = I.IDATLETA
            AND I.IDEVENTO = %s
            AND I.IDITEM = %s
            ORDER BY CONCAT(A.NOME,' ',A.SOBRENOME)
            """
            cursor.execute(query, (evento_id, modalidade_id))
        else:
            query = """
            SELECT CONCAT(COALESCE(I.NUPEITO, ''),' ',A.NOME,' ',A.SOBRENOME) AS ATLETA, 
                   I.CAMISETA,
                   EV.DESCRICAO,
                   I.IDINSCRICAO,
                   A.SEXO,
                   I.FLSTATUS,
                   I.NUPEITO
            FROM ATLETA A, INSCRICAO I, EVENTO_MODALIDADE EV
            WHERE 
            EV.IDITEM = I.IDITEM
            AND A.IDATLETA = I.IDATLETA
            AND I.IDEVENTO = %s
            ORDER BY CONCAT(A.NOME,' ',A.SOBRENOME)
            """
            cursor.execute(query, (evento_id,))
            
        inscricoes = cursor.fetchall()
        cursor.close()
        
        print(f"DEBUG: Encontradas {len(inscricoes)} inscrições")
        
        inscricoes_list = []
        for inscricao in inscricoes:
            inscricoes_list.append({
                'ATLETA': inscricao[0],
                'CAMISETA': inscricao[1],
                'DESCRICAO': inscricao[2],
                'IDINSCRICAO': inscricao[3],
                'SEXO': inscricao[4],
                'FLSTATUS': inscricao[5],
                'NUPEITO': inscricao[6]
            })
        
        return jsonify(inscricoes_list)
        
    except Exception as e:
        print(f"DEBUG: Erro ao buscar inscrições: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Rota para buscar detalhes da inscrição
@app.route('/api/inscricao/<int:inscricao_id>')
def get_inscricao_detalhes(inscricao_id):
    print(f"DEBUG: Buscando detalhes da inscrição {inscricao_id}")
    
    if not session.get('autenticado'):
        print("DEBUG: Usuário não autenticado")
        return jsonify({'error': 'Não autenticado'}), 401
    
    try:
        cursor = mysql.connection.cursor()
        query = """
        SELECT I.IDINSCRICAO, I.CPF, I.APOIO, I.NOME_EQUIPE, I.INTEGRANTES,
            I.CAMISETA, I.VALOR, I.TAXA, I.DESCONTO, I.VALOR_PGTO,
            I.FORMAPGTO, I.EQUIPE, I.CUPOM, 
            CONCAT(A.NOME,' ',A.SOBRENOME) AS NOME_COMPLETO,
            A.DTNASCIMENTO, A.NRCELULAR, A.SEXO, A.IDATLETA,
            EV.DESCRICAO AS MODALIDADE, I.FLSTATUS, I.NUPEITO
        FROM INSCRICAO I
        JOIN ATLETA A ON A.IDATLETA = I.IDATLETA
        JOIN EVENTO_MODALIDADE EV ON EV.IDITEM = I.IDITEM
        WHERE I.IDINSCRICAO = %s
        """
        cursor.execute(query, (inscricao_id,))
        inscricao = cursor.fetchone()
        cursor.close()
        
        if inscricao:
            resultado = {
                'IDINSCRICAO': inscricao[0],
                'CPF': inscricao[1],
                'APOIO': inscricao[2],
                'NOME_EQUIPE': inscricao[3],
                'INTEGRANTES': inscricao[4],
                'CAMISETA': inscricao[5],
                'VALOR': float(inscricao[6]) if inscricao[6] else 0,
                'TAXA': float(inscricao[7]) if inscricao[7] else 0,
                'DESCONTO': float(inscricao[8]) if inscricao[8] else 0,
                'VALOR_PGTO': float(inscricao[9]) if inscricao[9] else 0,
                'FORMAPGTO': inscricao[10],
                'EQUIPE': inscricao[11],
                'CUPOM': inscricao[12],
                'NOME_COMPLETO': inscricao[13],
                'DTNASCIMENTO': inscricao[14],
                'NRCELULAR': inscricao[15],
                'SEXO': inscricao[16],
                'IDATLETA': inscricao[17], 
                'MODALIDADE': inscricao[18],
                'FLSTATUS': inscricao[19],
                'NUPEITO': inscricao[20]
            }
            print(f"DEBUG: Detalhes encontrados: {resultado}")
            return jsonify(resultado)
        else:
            print("DEBUG: Inscrição não encontrada")
            return jsonify({'error': 'Inscrição não encontrada'}), 404
            
    except Exception as e:
        print(f"DEBUG: Erro ao buscar detalhes: {str(e)}")
        return jsonify({'error': str(e)}), 500


# Rota para logout
@app.route('/logout_coordenador', methods=['POST'])
def logout_coordenador():
    print("DEBUG: Fazendo logout")
    session.pop('autenticado', None)
    return jsonify({'success': True})


# Rota para buscar equipes por evento
@app.route('/api/equipes/<int:evento_id>')
def get_equipes(evento_id):
    print(f"DEBUG: Buscando equipes para evento {evento_id}")
    
    if not session.get('autenticado'):
        return jsonify({'error': 'Não autenticado'}), 401
    
    try:
        cursor = mysql.connection.cursor()
        query = """
        SELECT E.IDEA, E.NOME_EQUIPE, EM.DESCRICAO
        FROM EQUIPE E, EVENTO_MODALIDADE EM
        WHERE EM.IDITEM = E.IDITEM
        AND E.IDEVENTO = %s
        ORDER BY E.NOME_EQUIPE
        """
        cursor.execute(query, (evento_id,))
        equipes = cursor.fetchall()
        cursor.close()
        
        print(f"DEBUG: Encontradas {len(equipes)} equipes")
        
        equipes_list = []
        for equipe in equipes:
            equipes_list.append({
                'IDEA': equipe[0],
                'NOME_EQUIPE': equipe[1],
                'DESCRICAO': equipe[2]
            })
        
        return jsonify(equipes_list)
        
    except Exception as e:
        print(f"DEBUG: Erro ao buscar equipes: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Rota para buscar dados de uma modalidade específica
@app.route('/api/modalidade1/<int:modalidade_id>')
def get_modalidade1(modalidade_id):
    print(f"DEBUG: Buscando modalidade {modalidade_id}")
    
    if not session.get('autenticado'):
        return jsonify({'error': 'Não autenticado'}), 401
    
    try:
        cursor = mysql.connection.cursor()
        query = """
        SELECT IDITEM, IDEVENTO, DESCRICAO, DISTANCIA, KM, 
               VLINSCRICAO, VLMEIA, VLTAXA, NU_ATLETAS
        FROM EVENTO_MODALIDADE 
        WHERE IDITEM = %s
        """
        cursor.execute(query, (modalidade_id,))
        modalidade = cursor.fetchone()
        cursor.close()
        
        if modalidade:
            modalidade_data = {
                'IDITEM': modalidade[0],
                'IDEVENTO': modalidade[1],
                'DESCRICAO': modalidade[2],
                'DISTANCIA': modalidade[3],
                'KM': modalidade[4],
                'VLINSCRICAO': float(modalidade[5]) if modalidade[5] else 0,
                'VLMEIA': float(modalidade[6]) if modalidade[6] else 0,
                'VLTAXA': float(modalidade[7]) if modalidade[7] else 0,
                'NU_ATLETAS': modalidade[8]
            }
            return jsonify(modalidade_data)
        else:
            return jsonify({'error': 'Modalidade não encontrada'}), 404
        
    except Exception as e:
        print(f"DEBUG: Erro ao buscar modalidade: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Rota para buscar atletas disponíveis para equipe
@app.route('/api/atletas-disponiveis/<int:evento_id>/<int:modalidade_id>')
def get_atletas_disponiveis(evento_id, modalidade_id):
    print(f"DEBUG: Buscando atletas disponíveis para evento {evento_id}, modalidade {modalidade_id}")
    
    if not session.get('autenticado'):
        return jsonify({'error': 'Não autenticado'}), 401
    
    try:
        cursor = mysql.connection.cursor()
        query = """
        SELECT A.IDATLETA, CONCAT(A.NOME,' ',A.SOBRENOME) AS ATLETA
        FROM INSCRICAO I, ATLETA A
        WHERE NOT EXISTS (
            SELECT 1 
            FROM EQUIPE_ATLETAS EA 
            WHERE EA.IDATLETA = A.IDATLETA 
            AND EA.IDEVENTO = %s
        )
        AND I.IDITEM = %s
        AND I.IDEVENTO = %s
        AND A.IDATLETA = I.IDATLETA
        ORDER BY CONCAT(A.NOME,' ',A.SOBRENOME)
        """
        cursor.execute(query, (evento_id, modalidade_id, evento_id))
        atletas = cursor.fetchall()
        cursor.close()
        
        print(f"DEBUG: Encontrados {len(atletas)} atletas disponíveis")
        
        atletas_list = []
        for atleta in atletas:
            atletas_list.append({
                'IDATLETA': atleta[0],
                'ATLETA': atleta[1]
            })
        
        return jsonify(atletas_list)
        
    except Exception as e:
        print(f"DEBUG: Erro ao buscar atletas disponíveis: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Rota para criar equipe
@app.route('/api/criar-equipe', methods=['POST'])
def criar_equipe():
    print("DEBUG: Criando nova equipe")
    
    if not session.get('autenticado'):
        return jsonify({'error': 'Não autenticado'}), 401
    
    try:
        data = request.json
        evento_id = data['eventoId']
        modalidade_id = data['modalidadeId']
        nome_equipe = data['nomeEquipe']
        atletas = data['atletas']
        
        print(f"DEBUG: Dados recebidos - Evento: {evento_id}, Modalidade: {modalidade_id}, Nome: {nome_equipe}")
        
        cursor = mysql.connection.cursor()
        
        # Buscar dados da modalidade para cálculos de KM
        cursor.execute("SELECT KM FROM EVENTO_MODALIDADE WHERE IDITEM = %s", (modalidade_id,))
        modalidade_data = cursor.fetchone()
        km_modalidade = modalidade_data[0] if modalidade_data else 0
        
        # Inserir equipe
        cursor.execute("""
            INSERT INTO EQUIPE (IDEVENTO, IDITEM, NOME_EQUIPE) 
            VALUES (%s, %s, %s)
        """, (evento_id, modalidade_id, nome_equipe))
        
        equipe_id = cursor.lastrowid
        print(f"DEBUG: Equipe criada com ID: {equipe_id}")
        
        # Inserir atletas da equipe
        for ordem, atleta in enumerate(atletas, 1):
            km_ini = (ordem - 1) * km_modalidade
            km_fim = ordem * km_modalidade
            
            cursor.execute("""
                INSERT INTO EQUIPE_ATLETAS (IDEA, IDEVENTO, IDATLETA, ORDEM, KM_INI, KM_FIM) 
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (equipe_id, evento_id, atleta['IDATLETA'], ordem, km_ini, km_fim))
            
            print(f"DEBUG: Atleta {atleta['NOME']} inserido - Ordem: {ordem}, KM: {km_ini}-{km_fim}")
        
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({'success': True, 'message': 'Equipe criada com sucesso'})
        
    except Exception as e:
        print(f"DEBUG: Erro ao criar equipe: {str(e)}")
        mysql.connection.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# Rota para buscar atletas de uma equipe
@app.route('/api/equipe-atletas/<int:equipe_id>')
def get_equipe_atletas(equipe_id):
    print(f"DEBUG: Buscando atletas da equipe {equipe_id}")
    
    if not session.get('autenticado'):
        return jsonify({'error': 'Não autenticado'}), 401
    
    try:
        cursor = mysql.connection.cursor()
        
        # Buscar dados da equipe
        cursor.execute("""
            SELECT E.IDEA, E.NOME_EQUIPE, E.IDEVENTO, E.IDITEM, EM.DESCRICAO
            FROM EQUIPE E, EVENTO_MODALIDADE EM
            WHERE E.IDEA = %s AND EM.IDITEM = E.IDITEM
        """, (equipe_id,))
        equipe_data = cursor.fetchone()
        
        if not equipe_data:
            return jsonify({'error': 'Equipe não encontrada'}), 404
        
        # Buscar atletas da equipe
        cursor.execute("""
            SELECT EA.IDATLETA, CONCAT(A.NOME,' ',A.SOBRENOME) AS ATLETA, 
                   EA.ORDEM, EA.KM_INI, EA.KM_FIM
            FROM EQUIPE_ATLETAS EA
            INNER JOIN ATLETA A ON A.IDATLETA = EA.IDATLETA
            WHERE EA.IDEA = %s
            ORDER BY EA.ORDEM
        """, (equipe_id,))
        atletas_data = cursor.fetchall()
        
        cursor.close()
        
        # Estruturar dados da equipe
        equipe = {
            'IDEA': equipe_data[0],
            'NOME_EQUIPE': equipe_data[1],
            'IDEVENTO': equipe_data[2],
            'IDITEM': equipe_data[3],
            'DESCRICAO': equipe_data[4]
        }
        
        # Estruturar dados dos atletas
        atletas = []
        for atleta in atletas_data:
            atletas.append({
                'IDATLETA': atleta[0],
                'ATLETA': atleta[1],
                'ORDEM': atleta[2],
                'KM_INI': atleta[3],
                'KM_FIM': atleta[4]
            })
        
        return jsonify({
            'equipe': equipe,
            'atletas': atletas
        })
        
    except Exception as e:
        print(f"Erro ao buscar atletas da equipe: {str(e)}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

# Rota para salvar nova ordem dos atletas
@app.route('/api/salvar-ordem-equipe', methods=['POST'])
def salvar_ordem_equipe():
    print("DEBUG: Salvando nova ordem da equipe")
    
    if not session.get('autenticado'):
        return jsonify({'error': 'Não autenticado'}), 401
    
    try:
        data = request.get_json()
        equipe_id = data.get('equipeId')
        atletas = data.get('atletas')
        
        if not all([equipe_id, atletas]):
            return jsonify({'error': 'Dados incompletos'}), 400
        
        cursor = mysql.connection.cursor()
        
        # Buscar dados da equipe para pegar o KM da modalidade
        cursor.execute("""
            SELECT E.IDITEM, EM.KM
            FROM EQUIPE E
            INNER JOIN EVENTO_MODALIDADE EM ON EM.IDITEM = E.IDITEM
            WHERE E.IDEA = %s
        """, (equipe_id,))
        equipe_data = cursor.fetchone()
        
        if not equipe_data:
            return jsonify({'error': 'Equipe não encontrada'}), 404
        
        km_por_atleta = equipe_data[1]
        
        # Atualizar ordem dos atletas
        for atleta in atletas:
            ordem = atleta['ordem']
            id_atleta = atleta['idatleta']
            km_ini = (ordem - 1) * km_por_atleta
            km_fim = ordem * km_por_atleta
            
            cursor.execute("""
                UPDATE EQUIPE_ATLETAS 
                SET ORDEM = %s, KM_INI = %s, KM_FIM = %s
                WHERE IDEA = %s AND IDATLETA = %s
            """, (ordem, km_ini, km_fim, equipe_id, id_atleta))
        
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({'success': True, 'message': 'Ordem salva com sucesso'})
        
    except Exception as e:
        print(f"Erro ao salvar ordem: {str(e)}")
        mysql.connection.rollback()
        return jsonify({'error': 'Erro interno do servidor'}), 500

@app.route('/api/apoios/<int:atleta_id>')
def get_apoios_atleta(atleta_id):
    print(f"DEBUG: Buscando apoios do atleta {atleta_id}")
    
    if not session.get('autenticado'):
        print("DEBUG: Usuário não autenticado")
        return jsonify({'error': 'Não autenticado'}), 401
    
    try:
        cursor = mysql.connection.cursor()
        query = """
        SELECT IDAPOIO, NOME, CELULAR, VEICULO, PLACA
        FROM APOIO 
        WHERE IDATLETA = %s
        ORDER BY NOME
        """
        cursor.execute(query, (atleta_id,))
        apoios = cursor.fetchall()
        cursor.close()
        
        resultado = []
        for apoio in apoios:
            veiculo_placa = ""
            if apoio[3] or apoio[4]:  # Se tem veículo ou placa
                veiculo = apoio[3] or ""
                placa = apoio[4] or ""
                veiculo_placa = f"{veiculo} {placa}".strip()
            
            resultado.append({
                'IDAPOIO': apoio[0],
                'NOME': apoio[1],
                'CELULAR': apoio[2],
                'VEICULO_PLACA': veiculo_placa
            })
        
        print(f"DEBUG: {len(resultado)} apoios encontrados")
        return jsonify(resultado)
        
    except Exception as e:
        print(f"DEBUG: Erro ao buscar apoios: {str(e)}")
        return jsonify({'error': str(e)}), 500

# @app.route('/apoio_organizacao200k')
# def apoio_organizacao200k():
#     """Rota para servir a página HTML de cadastro de apoio"""
#     return render_template('apoio_organizacao200k.html')

@app.route('/obter_pontos_apoio_org200k', methods=['GET'])
def obter_pontos_apoio_org200k():
    """Rota para obter todos os pontos de apoio disponíveis"""
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT IDPONTO, DE_PONTO 
            FROM PONTO_APOIO_ORG_200k 
            ORDER BY IDPONTO
        """)
        rows = cur.fetchall()
        cur.close()
        
        pontos = []
        for row in rows:
            pontos.append({
                'IDPONTO': row[0],
                'DE_PONTO': row[1]
            })
        
        return jsonify(pontos)
    
    except Exception as e:
        return jsonify({'error': f'Erro ao obter pontos de apoio: {str(e)}'}), 500

@app.route('/obter_proximo_id_apoio_org200k', methods=['GET'])
def obter_proximo_id_apoio_org200k():
    """Rota para obter o próximo ID disponível para APOIO_ORG_200k"""
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT COALESCE(MAX(IDAPOIO_ORG), 0) + 1 as proximo_id 
            FROM APOIO_ORG_200k
        """)
        row = cur.fetchone()
        cur.close()
        
        proximo_id = row[0] if row else 1
        
        return jsonify({'proximo_id': proximo_id})
    
    except Exception as e:
        return jsonify({'error': f'Erro ao obter próximo ID: {str(e)}'}), 500

@app.route('/salvar_apoio_org200k', methods=['POST'])
def salvar_apoio_org200k():
    """Rota para salvar o apoio da organização e seus itens"""
    try:
        print("=== INICIO salvar_apoio_org200k ===")
        
        dados = request.get_json()
        print(f"Dados recebidos: {dados}")
        
        # Validar dados recebidos
        if not dados:
            print("Erro: Dados não informados")
            return jsonify({'message': 'Dados não informados'}), 400
        
        id_apoio_org = dados.get('idApoioOrg')
        nome = dados.get('nome', '').strip()
        celular = dados.get('celular', '').replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        itens = dados.get('itens', [])
        
        print(f"ID: {id_apoio_org}, Nome: {nome}, Celular: {celular}")
        print(f"Itens: {itens}")
        
        # Validações
        if not nome:
            print("Erro: Nome é obrigatório")
            return jsonify({'message': 'Nome é obrigatório'}), 400
        
        if not celular or len(celular) != 11:
            print(f"Erro: Celular inválido - {celular} - tamanho: {len(celular)}")
            return jsonify({'message': 'Celular deve ter 11 dígitos'}), 400
        
        if not itens:
            print("Erro: Nenhum item de apoio")
            return jsonify({'message': 'Pelo menos um item de apoio é obrigatório'}), 400
        
        if not id_apoio_org:
            print("Erro: ID do apoio não informado")
            return jsonify({'message': 'ID do apoio não informado'}), 400
        
        # Validar datas dos itens
        print("Validando datas dos itens...")
        data_minima = datetime(2025, 7, 4, 12, 0)
        data_maxima = datetime(2025, 7, 6, 19, 0)
        
        for i, item in enumerate(itens):
            print(f"Validando item {i}: {item}")
            try:
                dt_inicio = datetime.fromisoformat(item['DTHR_INICIO'].replace('T', ' '))
                dt_final = datetime.fromisoformat(item['DTHR_FINAL'].replace('T', ' '))
                
                print(f"Item {i} - Início: {dt_inicio}, Final: {dt_final}")
                
                if dt_inicio < data_minima or dt_inicio > data_maxima:
                    print(f"Erro: Data início fora do intervalo - {dt_inicio}")
                    return jsonify({'message': 'Data/hora de início deve estar entre 04/07/2025 12:00 e 06/07/2025 19:00'}), 400
                
                if dt_final < data_minima or dt_final > data_maxima:
                    print(f"Erro: Data final fora do intervalo - {dt_final}")
                    return jsonify({'message': 'Data/hora final deve estar entre 04/07/2025 12:00 e 06/07/2025 19:00'}), 400
                
                if dt_final <= dt_inicio:
                    print(f"Erro: Data final <= início")
                    return jsonify({'message': 'Data/hora final deve ser posterior à data/hora inicial'}), 400
                    
            except ValueError as ve:
                print(f"Erro no formato da data: {ve}")
                return jsonify({'message': 'Formato de data/hora inválido'}), 400
            except Exception as e:
                print(f"Erro inesperado na validação de data: {e}")
                return jsonify({'message': f'Erro na validação de data: {str(e)}'}), 400
        
        # Iniciar transação
        print("Iniciando transação com banco de dados...")
        cur = None
        
        try:
            cur = mysql.connection.cursor()
            print("Cursor criado com sucesso")
            
            # Verificar se o ID já existe
            print(f"Verificando se ID {id_apoio_org} já existe...")
            cur.execute("SELECT COUNT(*) FROM APOIO_ORG_200k WHERE IDAPOIO_ORG = %s", (id_apoio_org,))
            count = cur.fetchone()[0]
            print(f"Registros encontrados com este ID: {count}")
            
            if count > 0:
                print("Erro: ID já existe")
                return jsonify({'message': 'ID já existe, recarregue a página'}), 400
            
            # Inserir registro principal na APOIO_ORG_200k
            print("Inserindo registro principal...")
            sql_principal = """
                INSERT INTO APOIO_ORG_200k (IDAPOIO_ORG, NOME, CELULAR, DT_CADASTRO) 
                VALUES (%s, %s, %s, NOW())
            """
            parametros_principal = (id_apoio_org, nome, celular)
            print(f"SQL: {sql_principal}")
            print(f"Parâmetros: {parametros_principal}")
            
            cur.execute(sql_principal, parametros_principal)
            print("Registro principal inserido com sucesso")
            
            # Inserir itens na APOIO_ORG_ITENS_200k
            print("Inserindo itens...")
            for i, item in enumerate(itens):
                dt_inicio_str = item['DTHR_INICIO'].replace('T', ' ')
                dt_final_str = item['DTHR_FINAL'].replace('T', ' ')
                
                # Correção: usar IDPUNTO ao invés de IDPONTO (conforme enviado do frontend)
                id_ponto = item.get('IDPUNTO') or item.get('IDPONTO')
                print(f"Item {i} - ID Ponto: {id_ponto}, Início: {dt_inicio_str}, Final: {dt_final_str}")
                
                sql_item = """
                    INSERT INTO APOIO_ORG_ITENS_200k (IDAPOIO_ORG, IDPONTO, DTHR_INICIO, DTHR_FINAL) 
                    VALUES (%s, %s, %s, %s)
                """
                parametros_item = (id_apoio_org, id_ponto, dt_inicio_str, dt_final_str)
                print(f"SQL Item: {sql_item}")
                print(f"Parâmetros Item: {parametros_item}")
                
                cur.execute(sql_item, parametros_item)
                print(f"Item {i} inserido com sucesso")
            
            # Confirmar transação
            print("Confirmando transação...")
            mysql.connection.commit()
            print("Transação confirmada com sucesso")
            
            return jsonify({
                'success': True, 
                'message': 'Apoio registrado com sucesso!',
                'id_apoio': id_apoio_org
            })
        
        except Exception as e:
            # Desfazer transação em caso de erro
            print(f"ERRO na transação do banco: {str(e)}")
            print(f"Tipo do erro: {type(e)}")
            import traceback
            traceback.print_exc()
            
            if mysql.connection:
                mysql.connection.rollback()
                print("Rollback executado")
            
            return jsonify({'message': f'Erro ao salvar no banco de dados: {str(e)}'}), 500
        
        finally:
            # Garantir que o cursor seja fechado
            if cur:
                cur.close()
                print("Cursor fechado")
    
    except Exception as e:
        print(f"ERRO GERAL na rota: {str(e)}")
        print(f"Tipo do erro: {type(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'message': f'Erro interno do servidor: {str(e)}'}), 500


@app.route('/consultar_apoio_org200k/<int:id_apoio>', methods=['GET'])
def consultar_apoio_org200k(id_apoio):
    """Rota para consultar um apoio específico (para futura página de edição)"""
    try:
        cur = mysql.connection.cursor()
        
        # Buscar dados principais
        cur.execute("""
            SELECT IDAPOIO_ORG, NOME, CELULAR, DT_CADASTRO 
            FROM APOIO_ORG_200k 
            WHERE IDAPOIO_ORG = %s
        """, (id_apoio,))
        
        apoio_row = cur.fetchone()
        if not apoio_row:
            cur.close()
            return jsonify({'error': 'Apoio não encontrado'}), 404
        
        # Buscar itens
        cur.execute("""
            SELECT ai.ID, ai.IDPONTO, p.DE_PONTO, ai.DTHR_INICIO, ai.DTHR_FINAL
            FROM APOIO_ORG_ITENS_200k ai
            INNER JOIN PONTO_APOIO_ORG_200k p ON ai.IDPONTO = p.IDPONTO
            WHERE ai.IDAPOIO_ORG = %s
            ORDER BY ai.DTHR_INICIO
        """, (id_apoio,))
        
        itens_rows = cur.fetchall()
        cur.close()
        
        # Montar resposta
        apoio = {
            'IDAPOIO_ORG': apoio_row[0],
            'NOME': apoio_row[1],
            'CELULAR': apoio_row[2],
            'DT_CADASTRO': apoio_row[3].isoformat() if apoio_row[3] else None,
            'itens': []
        }
        
        for item_row in itens_rows:
            apoio['itens'].append({
                'ID': item_row[0],
                'IDPONTO': item_row[1],
                'DE_PONTO': item_row[2],
                'DTHR_INICIO': item_row[3].isoformat() if item_row[3] else None,
                'DTHR_FINAL': item_row[4].isoformat() if item_row[4] else None
            })
        
        return jsonify(apoio)
    
    except Exception as e:
        return jsonify({'error': f'Erro ao consultar apoio: {str(e)}'}), 500

@app.route('/listar_apoios_org200k', methods=['GET'])
def listar_apoios_org200k():
    """Rota para listar todos os apoios (para futura página de administração)"""
    try:
        cur = mysql.connection.cursor()
        
        cur.execute("""
            SELECT a.IDAPOIO_ORG, a.NOME, a.CELULAR, a.DT_CADASTRO,
                   COUNT(ai.ID) as total_itens
            FROM APOIO_ORG_200k a
            LEFT JOIN APOIO_ORG_ITENS_200k ai ON a.IDAPOIO_ORG = ai.IDAPOIO_ORG
            GROUP BY a.IDAPOIO_ORG, a.NOME, a.CELULAR, a.DT_CADASTRO
            ORDER BY a.DT_CADASTRO DESC
        """)
        
        rows = cur.fetchall()
        cur.close()
        
        apoios = []
        for row in rows:
            apoios.append({
                'IDAPOIO_ORG': row[0],
                'NOME': row[1],
                'CELULAR': row[2],
                'DT_CADASTRO': row[3].isoformat() if row[3] else None,
                'TOTAL_ITENS': row[4]
            })
        
        return jsonify(apoios)
    
    except Exception as e:
        return jsonify({'error': f'Erro ao listar apoios: {str(e)}'}), 500

# Função auxiliar para popular tabela de pontos de apoio (execute uma vez)
@app.route('/popular_pontos_apoio_org200k', methods=['POST'])
def popular_pontos_apoio_org200k():
    """Rota para popular a tabela de pontos de apoio (usar apenas uma vez para configurar)"""
    try:
        pontos_exemplo = [
            'Largada',
            'KM 5',
            'KM 10',
            'KM 20',
            'KM 30',
            'KM 50',
            'KM 70',
            'KM 100',
            'KM 130',
            'KM 150',
            'KM 170',
            'KM 190',
            'Chegada',
            'Posto Médico',
            'Hidratação',
            'Apoio Técnico'
        ]
        
        cur = mysql.connection.cursor()
        
        for ponto in pontos_exemplo:
            cur.execute("""
                INSERT INTO PONTO_APOIO_ORG_200k (DE_PONTO) 
                VALUES (%s)
            """, (ponto,))
        
        mysql.connection.commit()
        cur.close()
        
        return jsonify({'success': True, 'message': 'Pontos de apoio populados com sucesso!'})
    
    except Exception as e:
        return jsonify({'error': f'Erro ao popular pontos de apoio: {str(e)}'}), 500

# Rota para excluir um apoio (para futura página de administração)
@app.route('/excluir_apoio_org200k/<int:id_apoio>', methods=['DELETE'])
def excluir_apoio_org200k(id_apoio):
    """Rota para excluir um apoio e seus itens"""
    try:
        cur = mysql.connection.cursor()
        
        try:
            # Excluir itens primeiro (chave estrangeira)
            cur.execute("DELETE FROM APOIO_ORG_ITENS_200k WHERE IDAPOIO_ORG = %s", (id_apoio,))
            
            # Excluir apoio principal
            cur.execute("DELETE FROM APOIO_ORG_200k WHERE IDAPOIO_ORG = %s", (id_apoio,))
            
            if cur.rowcount == 0:
                mysql.connection.rollback()
                cur.close()
                return jsonify({'error': 'Apoio não encontrado'}), 404
            
            mysql.connection.commit()
            cur.close()
            
            return jsonify({'success': True, 'message': 'Apoio excluído com sucesso!'})
        
        except Exception as e:
            mysql.connection.rollback()
            cur.close()
            return jsonify({'error': f'Erro ao excluir apoio: {str(e)}'}), 500
    
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500


@app.route('/api/apoio-admin002', methods=['GET'])
def listar_apoio_admin002():
    """Lista todos os registros de apoio com seus itens"""
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT 
                a.IDAPOIO_ORG,
                a.NOME,
                a.CELULAR,
                ai.ID as ITEM_ID,
                ai.IDPONTO,
                p.DE_PONTO,
                ai.DTHR_INICIO,
                ai.DTHR_FINAL
            FROM APOIO_ORG_200k a
            LEFT JOIN APOIO_ORG_ITENS_200k ai ON a.IDAPOIO_ORG = ai.IDAPOIO_ORG
            LEFT JOIN PONTO_APOIO_ORG_200k p ON ai.IDPONTO = p.IDPONTO
            ORDER BY a.IDAPOIO_ORG, ai.ID
        """)
        
        registros = cur.fetchall()
        cur.close()
        
        # Organizar dados por apoiador
        apoiadores = {}
        for registro in registros:
            id_apoio = registro[0]
            if id_apoio not in apoiadores:
                apoiadores[id_apoio] = {
                    'IDAPOIO_ORG': registro[0],
                    'NOME': registro[1],
                    'CELULAR': registro[2],
                    'itens': []
                }
            
            if registro[3]:  # Se tem item
                apoiadores[id_apoio]['itens'].append({
                    'ID': registro[3],
                    'IDPONTO': registro[4],
                    'DE_PONTO': registro[5],
                    'DTHR_INICIO': registro[6].strftime('%Y-%m-%dT%H:%M') if registro[6] else '',
                    'DTHR_FINAL': registro[7].strftime('%Y-%m-%dT%H:%M') if registro[7] else ''
                })
        
        return jsonify(list(apoiadores.values()))
    
    except Exception as e:
        return jsonify({'error': f'Erro ao listar apoio: {str(e)}'}), 500


@app.route('/api/pontos-apoio002', methods=['GET'])
def listar_pontos_apoio002():
    """Lista todos os pontos de apoio disponíveis"""
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT IDPONTO, DE_PONTO FROM PONTO_APOIO_ORG_200k ORDER BY IDPONTO")
        pontos = cur.fetchall()
        cur.close()
        
        pontos_list = []
        for ponto in pontos:
            pontos_list.append({
                'IDPONTO': ponto[0],
                'DE_PONTO': ponto[1]
            })
        
        return jsonify(pontos_list)
    
    except Exception as e:
        return jsonify({'error': f'Erro ao listar pontos: {str(e)}'}), 500

@app.route('/api/apoio-item002/<int:item_id>', methods=['PUT'])
def atualizar_item_apoio002(item_id):
    """Atualiza um item de apoio (datas/horários e ponto)"""
    try:
        data = request.json
        cur = mysql.connection.cursor()
        
        cur.execute("""
            UPDATE APOIO_ORG_ITENS_200k 
            SET IDPONTO = %s, DTHR_INICIO = %s, DTHR_FINAL = %s
            WHERE ID = %s
        """, (
            data.get('IDPONTO'),
            data.get('DTHR_INICIO') if data.get('DTHR_INICIO') else None,
            data.get('DTHR_FINAL') if data.get('DTHR_FINAL') else None,
            item_id
        ))
        
        mysql.connection.commit()
        cur.close()
        
        return jsonify({'success': 'Item atualizado com sucesso'})
    
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'error': f'Erro ao atualizar item: {str(e)}'}), 500

@app.route('/api/apoio-org002/<int:apoio_id>', methods=['DELETE'])
def excluir_apoio002(apoio_id):
    """Exclui um apoiador e todos os seus itens"""
    try:
        cur = mysql.connection.cursor()
        
        # Primeiro exclui os itens
        cur.execute("DELETE FROM APOIO_ORG_ITENS_200k WHERE IDAPOIO_ORG = %s", (apoio_id,))
        
        # Depois exclui o apoiador
        cur.execute("DELETE FROM APOIO_ORG_200k WHERE IDAPOIO_ORG = %s", (apoio_id,))
        
        mysql.connection.commit()
        cur.close()
        
        return jsonify({'success': 'Apoiador excluído com sucesso'})
    
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'error': f'Erro ao excluir apoiador: {str(e)}'}), 500

@app.route('/api/apoio-item002/<int:item_id>', methods=['DELETE'])
def excluir_item_apoio002(item_id):
    """Exclui apenas um item específico de apoio"""
    try:
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM APOIO_ORG_ITENS_200k WHERE ID = %s", (item_id,))
        mysql.connection.commit()
        cur.close()
        
        return jsonify({'success': 'Item excluído com sucesso'})
    
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'error': f'Erro ao excluir item: {str(e)}'}), 500

@app.route('/admin-apoio')
def admin_apoio002():
    """Página de administração do apoio"""
    return render_template('admin_apoio002.html')

#############################
#@app.route('/cronometro200k')
#def cronometro200k():
#    """Página do cronômetro da ultramaratona"""
#    return render_template('cronometro200k.html')

@app.route('/painel200k')
def painel200k():
    """Página do cronômetro da ultramaratona"""
    return render_template('cronometro200k.html')

@app.route('/api/evento-data', methods=['GET'])
def obter_data_evento():
    """Rota para obter a data/hora do evento"""
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT DATAHORAEVENTO 
            FROM EVENTO1 
            WHERE IDEVENTO = 1
        """)
        row = cur.fetchone()
        cur.close()
        
        if row:
            # Converter para timestamp (assumindo que o banco está em horário local)
            data_evento = row[0]
            
            # Se necessário, ajustar timezone (exemplo para Rondônia - UTC-4)
            if data_evento.tzinfo is None:
                # Assumir que é horário local de Rondônia
                tz_rondonia = pytz.timezone('America/Porto_Velho')
                data_evento = tz_rondonia.localize(data_evento)
            
            # Converter para timestamp em milissegundos
            timestamp = int(data_evento.timestamp() * 1000)
            
            return jsonify({
                'success': True,
                'dataHoraEvento': data_evento.isoformat(),
                'timestamp': timestamp
            })
        else:
            return jsonify({'success': False, 'error': 'Evento não encontrado'}), 404
    
    except Exception as e:
        return jsonify({'success': False, 'error': f'Erro ao obter data do evento: {str(e)}'}), 500

@app.route('/api/iniciar-cronometro', methods=['POST'])
def iniciar_cronometro():
    """Rota para marcar o início da corrida (opcional - para controle manual)"""
    try:
        # Atualizar a data/hora do evento para agora
        cur = mysql.connection.cursor()
        cur.execute("""
            UPDATE EVENTO 
            SET DATAHORAEVENTO = NOW() 
            WHERE IDEVENTO = 1
        """)
        mysql.connection.commit()
        cur.close()
        
        return jsonify({'success': True, 'message': 'Cronômetro iniciado!'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': f'Erro ao iniciar cronômetro: {str(e)}'}), 500



@app.route('/api/passagens-atletas', methods=['GET'])
def listar_passagens_atletas():
    """Lista as passagens mais recentes dos atletas nas parciais"""
    try:
        cur = mysql.connection.cursor()
        
        # Executa a SQL que você forneceu
        query = """
        SELECT p.IDATLETA, p.IDEA, p.DATA_HORA, p.KM, a.NOME,
          CASE 
            WHEN p.IDEA = 0 THEN 'Solo'
            ELSE (
              SELECT CONCAT(e.NOME_EQUIPE, ' (', em.DEREDUZ, ')')
              FROM EQUIPE e
              JOIN EVENTO_MODALIDADE em ON em.IDITEM = e.IDITEM
              WHERE e.IDEA = p.IDEA
            )
          END AS EQUIPE
        FROM PROVA_PARCIAIS_200K p
        JOIN ATLETA a ON a.IDATLETA = p.IDATLETA
        WHERE p.IDPARCIAL > 1
          AND (
            (p.IDEA = 0 AND p.DATA_HORA = (
              SELECT MAX(p2.DATA_HORA)
              FROM PROVA_PARCIAIS_200K p2
              WHERE p2.IDEA = 0 AND p2.IDATLETA = p.IDATLETA AND p2.IDPARCIAL > 1
            ))
            OR
            (p.IDEA > 0 AND p.DATA_HORA = (
              SELECT MAX(p3.DATA_HORA)
              FROM PROVA_PARCIAIS_200K p3
              WHERE p3.IDEA = p.IDEA AND p3.IDPARCIAL > 1
            ))
          )
        ORDER BY p.KM DESC, p.DATA_HORA;
        """
        
        cur.execute(query)
        passagens = cur.fetchall()
        cur.close()
        
        passagens_list = []
        for passagem in passagens:
            passagens_list.append({
                'IDATLETA': passagem[0],
                'IDEA': passagem[1],
                'DATA_HORA': passagem[2].isoformat() if passagem[2] else None,
                'KM': passagem[3],
                'NOME': passagem[4],
                'EQUIPE': passagem[5] if passagem[5] else 'Solo'
            })
        
        return jsonify({
            'success': True,
            'passagens': passagens_list
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erro ao listar passagens: {str(e)}'
        }), 500


###### CERTIFICADO #############
@app.route('/certificado200k')
def certificado200k():
    """Página para acessar o certificado"""
    return render_template('certificado200k.html')

@app.route('/certificado200k_buscar_atleta', methods=['POST'])
def certificado200k_buscar_atleta():
    """Busca os dados do atleta e retorna as informações para o certificado"""
    try:
        data = request.get_json()
        cpf = data.get('cpf', '').replace('.', '').replace('-', '').replace(' ', '')
        datanasc = data.get('datanasc', '')
        
        if not cpf or not datanasc:
            return jsonify({'success': False, 'message': 'CPF e data de nascimento são obrigatórios'})
        
        # Verificar se CPF tem 11 dígitos
        if len(cpf) != 11 or not cpf.isdigit():
            return jsonify({'success': False, 'message': 'CPF deve ter 11 dígitos numéricos'})
        
        cur = mysql.connection.cursor()
        
        # Primeiro, verificar se o atleta existe
        cur.execute("""
            SELECT IDATLETA, CONCAT(NOME, ' ', SOBRENOME) AS NOME_COMPLETO, 
                   CPF, DATANASC
            FROM ATLETA 
            WHERE CPF = %s AND DATANASC = %s
        """, (cpf, datanasc))
        
        atleta = cur.fetchone()
        
        if not atleta:
            cur.close()
            return jsonify({'success': False, 'message': 'Atleta não encontrado com os dados informados'})
        
        idatleta = atleta[0]
        nome_completo = atleta[1]
        
        # Verificar se é modalidade solo ou equipe
        dados_certificado = None
        
        # Primeiro, tentar buscar dados da modalidade Solo
        cur.execute("""
            SELECT CONCAT(a.NOME,' ',a.SOBRENOME) AS NOME, 200 AS KM_PERCORRIDO, 
            (SELECT DATA_HORA FROM PROVA_PARCIAIS_200K WHERE KM = 0 AND IDATLETA = a.IDATLETA) As DATA_HORA_LARGADA,
            (SELECT KM FROM PROVA_PARCIAIS_200K WHERE KM = 0 AND IDATLETA = a.IDATLETA) As KM_LARGADA,
            (SELECT DATA_HORA FROM PROVA_PARCIAIS_200K WHERE KM = 200 AND IDATLETA = a.IDATLETA) As DATA_HORA_CHEGADA,
            (SELECT KM FROM PROVA_PARCIAIS_200K WHERE KM = 200 AND IDATLETA = a.IDATLETA) As KM_CHEGADA,
            SEC_TO_TIME(TIMESTAMPDIFF(SECOND, 
              (SELECT DATA_HORA FROM PROVA_PARCIAIS_200K WHERE KM = 0 AND IDATLETA = a.IDATLETA), 
              (SELECT DATA_HORA FROM PROVA_PARCIAIS_200K WHERE KM = 200 AND IDATLETA = a.IDATLETA))) 
              AS TEMPO_TOTAL,
              (SELECT DETALHE FROM EVENTO_1 WHERE IDEVENTO = 1) AS DATAFIM
            FROM ATLETA a
            WHERE a.IDATLETA = %s
        """, (idatleta,))
        
        resultado_solo = cur.fetchone()
        
        if resultado_solo and resultado_solo[6] and resultado_solo[4]:  # Se tem tempo total e chegada
            dados_certificado = {
                'nome': resultado_solo[0],
                'modalidade': 'SOLO',
                'km_percorrido': resultado_solo[1],
                'data_hora_largada': resultado_solo[2],
                'data_hora_chegada': resultado_solo[4],
                'tempo_total': resultado_solo[6],
                'data_prova': resultado_solo[7]
            }
        else:
            # Se não encontrou dados solo, buscar dados de equipe
            cur.execute("""
                SELECT CONCAT(a.NOME,' ',a.SOBRENOME) AS NOME, (ea.KM_FIM - ea.KM_INI) AS KM_PERCORRIDO,
                (SELECT DATA_HORA FROM PROVA_PARCIAIS_200K WHERE KM = ea.KM_INI AND IDEA = ea.IDEA) As DATA_HORA_LARGADA,
                (SELECT KM FROM PROVA_PARCIAIS_200K WHERE KM = ea.KM_INI AND IDEA = ea.IDEA) As KM_LARGADA,
                (SELECT DATA_HORA FROM PROVA_PARCIAIS_200K WHERE KM = ea.KM_FIM AND IDEA = ea.IDEA) As DATA_HORA_CHEGADA,
                (SELECT KM FROM PROVA_PARCIAIS_200K WHERE KM = ea.KM_FIM AND IDEA = ea.IDEA) As KM_CHEGADA,
                SEC_TO_TIME(TIMESTAMPDIFF(SECOND, 
                  (SELECT DATA_HORA FROM PROVA_PARCIAIS_200K WHERE KM = ea.KM_INI AND IDEA = ea.IDEA), 
                  (SELECT DATA_HORA FROM PROVA_PARCIAIS_200K WHERE KM = ea.KM_FIM AND IDEA = ea.IDEA))) 
                  AS TEMPO_TOTAL,
                ea.KM_INI, ea.KM_FIM, (SELECT DETALHE FROM EVENTO_1 WHERE IDEVENTO = 1) AS DATAFIM
                FROM ATLETA a, EQUIPE_ATLETAS ea
                WHERE ea.IDATLETA = a.IDATLETA 
                AND a.IDATLETA = %s
            """, (idatleta,))
            
            resultado_equipe = cur.fetchone()
            
	   # 'data_prova': resultado_solo[2].strftime('%d/%m/%Y') if resultado_solo[2] else datetime.now().strftime('%d/%m/%Y')
		
            if resultado_equipe and resultado_equipe[6] and resultado_equipe[4]:  # Se tem tempo total e chegada
                # Determinar modalidade baseada na distância
                km_percorrido = resultado_equipe[1]
                if km_percorrido == 100:
                    modalidade = 'DUPLA'
                elif km_percorrido == 50:
                    modalidade = 'QUARTETO'
                elif km_percorrido == 25:
                    modalidade = 'OCTETO'
                else:
                    modalidade = 'EQUIPE'
                
                dados_certificado = {
                    'nome': resultado_equipe[0],
                    'modalidade': modalidade,
                    'km_percorrido': resultado_equipe[1],
                    'data_hora_largada': resultado_equipe[2],
                    'data_hora_chegada': resultado_equipe[4],
                    'tempo_total': resultado_equipe[6],
                    'data_prova': resultado_equipe[9]
                }
        
        cur.close()
        
        if not dados_certificado:
            return jsonify({'success': False, 'message': 'Atleta não completou a prova ou dados não encontrados'})
        
        # Converter tempo para string se necessário
        tempo_str = dados_certificado['tempo_total']
        if hasattr(tempo_str, 'total_seconds'):
            tempo_total = tempo_str
            horas = int(tempo_total.total_seconds() // 3600)
            minutos = int((tempo_total.total_seconds() % 3600) // 60)
            segundos = int(tempo_total.total_seconds() % 60)
            tempo_str = f"{horas:02d}:{minutos:02d}:{segundos:02d}"
        
        return jsonify({
            'success': True,
            'dados': {
                'idatleta': idatleta,
                'nome': dados_certificado['nome'],
                'modalidade': dados_certificado['modalidade'],
                'km_percorrido': dados_certificado['km_percorrido'],
                'tempo_total': str(tempo_str),
                'data_prova': dados_certificado['data_prova']
            }
        })
        
    except Exception as e:
        print(f"Erro ao buscar atleta: {e}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'})

@app.route('/certificado200k_gerar_pdf', methods=['POST'])
def certificado200k_gerar_pdf():
    """Gera PDF do certificado para o atleta"""
    try:
        data = request.get_json()
        dados = data.get('dados', {})
        
        if not dados:
            return jsonify({'success': False, 'message': 'Dados do atleta são obrigatórios'})
        
        # Criar buffer para o PDF
        buffer = io.BytesIO()
        
        # Criar documento PDF em paisagem
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), 
                              leftMargin=2*cm, rightMargin=2*cm, 
                              topMargin=2*cm, bottomMargin=2*cm)
        
        # Estilos
        styles = getSampleStyleSheet()
        
        # Estilo para título
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        )
        
        # Estilo para subtítulo
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        )
        
        # Estilo para texto principal
        main_style = ParagraphStyle(
            'CustomMain',
            parent=styles['Normal'],
            fontSize=14,
            spaceAfter=20,
            alignment=TA_CENTER,
            leading=20
        )
        
        # Estilo para assinaturas
        signature_style = ParagraphStyle(
            'CustomSignature',
            parent=styles['Normal'],
            fontSize=12,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        )
        
        # Elementos do documento
        elements = []
        
        # Logo do evento (se existir)
        try:
            logo_path = "/static/img/logo_200k.png"
            if os.path.exists(logo_path):
                logo = Image(logo_path, width=3*inch, height=2*inch)
                logo.hAlign = 'CENTER'
                elements.append(logo)
                elements.append(Spacer(1, 20))
        except:
            pass
        
        # Título
        title = Paragraph("4º Desafio 200 K Porto Velho - Humaitá", title_style)
        elements.append(title)
        elements.append(Spacer(1, 30))
        
        # Certificado
        cert_title = Paragraph("CERTIFICADO DE PARTICIPAÇÃO", subtitle_style)
        elements.append(cert_title)
        elements.append(Spacer(1, 30))
        
        # Texto principal
        texto_principal = f"""
        <b>{dados['nome']}</b>, participou do 4º
        Desafio 200k Porto Velho - Humaitá, na
        modalidade <b>{dados['modalidade']}</b>, percorrendo a
        distância de <b>{dados['km_percorrido']}km</b>, no tempo líquido de
        <b>{dados['tempo_total']}</b>
        """
        
        main_text = Paragraph(texto_principal, main_style)
        elements.append(main_text)
        elements.append(Spacer(1, 40))
        
        # Data e local
        data_local = Paragraph(f"Porto Velho, {dados['data_prova']}", main_style)
        elements.append(data_local)
        elements.append(Spacer(1, 60))
        
        # Tabela de assinaturas
        signature_data = [
            ['', ''],
            ['Kelio Esteves Xavier', 'Manoel Alves Barbosa'],
            ['Diretor da Prova', 'Coordenador de Prova']
        ]
        
        signature_table = Table(signature_data, colWidths=[3.5*inch, 3.5*inch])
        signature_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, 1), 12),
            ('FONTNAME', (0, 2), (-1, 2), 'Helvetica'),
            ('FONTSIZE', (0, 2), (-1, 2), 10),
            ('LINEABOVE', (0, 1), (-1, 1), 1, colors.black),
            ('TOPPADDING', (0, 1), (-1, 1), 10),
            ('BOTTOMPADDING', (0, 2), (-1, 2), 20),
        ]))
        
        elements.append(signature_table)
        elements.append(Spacer(1, 40))
        
        # Logo da empresa organizadora
        try:
            mc_logo_path = "/static/img/MC_logo.jpg"
            if os.path.exists(mc_logo_path):
                mc_logo = Image(mc_logo_path, width=2*inch, height=1.5*inch)
                mc_logo.hAlign = 'RIGHT'
                elements.append(mc_logo)
        except:
            pass
        
        # Construir PDF
        doc.build(elements)
        
        # Retornar PDF
        buffer.seek(0)
        pdf_data = buffer.getvalue()
        buffer.close()
        
        # Codificar em base64 para enviar via JSON
        pdf_base64 = base64.b64encode(pdf_data).decode('utf-8')
        
        return jsonify({
            'success': True,
            'pdf_data': pdf_base64,
            'filename': f"certificado_{dados['nome'].replace(' ', '_')}.pdf"
        })
        
    except Exception as e:
        print(f"Erro ao gerar PDF: {e}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'})

@app.route('/certificado200k_download_pdf', methods=['POST'])
def certificado200k_download_pdf():
    """Baixa o PDF do certificado"""
    try:
        data = request.get_json()
        pdf_data = data.get('pdf_data', '')
        filename = data.get('filename', 'certificado.pdf')
        
        if not pdf_data:
            return jsonify({'success': False, 'message': 'Dados do PDF não fornecidos'})
        
        # Decodificar base64
        pdf_bytes = base64.b64decode(pdf_data)
        
        # Criar arquivo temporário
        buffer = io.BytesIO(pdf_bytes)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        print(f"Erro ao baixar PDF: {e}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'})

@app.route('/certificado200k_verificar_conclusao/<int:idatleta>')
def certificado200k_verificar_conclusao(idatleta):
    """Verifica se o atleta completou a prova (solo ou equipe)"""
    try:
        cur = mysql.connection.cursor()
        
        # Verificar conclusão solo
        cur.execute("""
            SELECT COUNT(*) as completou_solo
            FROM PROVA_PARCIAIS_200K 
            WHERE IDATLETA = %s AND KM = 200
        """, (idatleta,))
        
        resultado_solo = cur.fetchone()
        completou_solo = resultado_solo[0] > 0 if resultado_solo else False
        
        # Verificar conclusão equipe
        cur.execute("""
            SELECT COUNT(*) as completou_equipe
            FROM EQUIPE_ATLETAS ea
            JOIN PROVA_PARCIAIS_200K p ON p.IDEA = ea.IDEA AND p.KM = ea.KM_FIM
            WHERE ea.IDATLETA = %s
        """, (idatleta,))
        
        resultado_equipe = cur.fetchone()
        completou_equipe = resultado_equipe[0] > 0 if resultado_equipe else False
        
        cur.close()
        
        return jsonify({
            'completou_solo': completou_solo,
            'completou_equipe': completou_equipe,
            'completou_alguma': completou_solo or completou_equipe
        })
        
    except Exception as e:
        print(f"Erro ao verificar conclusão: {e}")
        return jsonify({'error': 'Erro interno do servidor'})

@app.route('/certificado200k_estatisticas')
def certificado200k_estatisticas():
    """Retorna estatísticas gerais da prova"""
    try:
        cur = mysql.connection.cursor()
        
        # Total de atletas inscritos
        cur.execute("SELECT COUNT(*) FROM ATLETA")
        total_atletas = cur.fetchone()[0]
        
        # Atletas que completaram solo
        cur.execute("""
            SELECT COUNT(DISTINCT IDATLETA) 
            FROM PROVA_PARCIAIS_200K 
            WHERE KM = 200
        """)
        completaram_solo = cur.fetchone()[0]
        
        # Atletas que completaram equipe
        cur.execute("""
            SELECT COUNT(DISTINCT ea.IDATLETA) 
            FROM EQUIPE_ATLETAS ea
            JOIN PROVA_PARCIAIS_200K p ON p.IDEA = ea.IDEA AND p.KM = ea.KM_FIM
        """)
        completaram_equipe = cur.fetchone()[0]
        
        # Melhor tempo solo
        cur.execute("""
            SELECT CONCAT(a.NOME, ' ', a.SOBRENOME) AS NOME,
                   SEC_TO_TIME(TIMESTAMPDIFF(SECOND, 
                     (SELECT DATA_HORA FROM PROVA_PARCIAIS_200K WHERE KM = 0 AND IDATLETA = a.IDATLETA), 
                     (SELECT DATA_HORA FROM PROVA_PARCIAIS_200K WHERE KM = 200 AND IDATLETA = a.IDATLETA))) AS TEMPO
            FROM ATLETA a
            WHERE EXISTS (SELECT 1 FROM PROVA_PARCIAIS_200K WHERE KM = 200 AND IDATLETA = a.IDATLETA)
            ORDER BY TIMESTAMPDIFF(SECOND, 
              (SELECT DATA_HORA FROM PROVA_PARCIAIS_200K WHERE KM = 0 AND IDATLETA = a.IDATLETA), 
              (SELECT DATA_HORA FROM PROVA_PARCIAIS_200K WHERE KM = 200 AND IDATLETA = a.IDATLETA))
            LIMIT 1
        """)
        melhor_tempo_solo = cur.fetchone()
        
        cur.close()
        
        return jsonify({
            'total_atletas': total_atletas,
            'completaram_solo': completaram_solo,
            'completaram_equipe': completaram_equipe,
            'total_completaram': completaram_solo + completaram_equipe,
            'melhor_tempo_solo': {
                'nome': melhor_tempo_solo[0] if melhor_tempo_solo else None,
                'tempo': str(melhor_tempo_solo[1]) if melhor_tempo_solo else None
            }
        })
        
    except Exception as e:
        print(f"Erro ao obter estatísticas: {e}")
        return jsonify({'error': 'Erro interno do servidor'})


@app.route('/certificado200k_validar_cpf', methods=['POST'])
def certificado200k_validar_cpf():
    """Valida CPF usando algoritmo padrão"""
    try:
        data = request.get_json()
        cpf = data.get('cpf', '').replace('.', '').replace('-', '').replace(' ', '')
        
        if not cpf or len(cpf) != 11 or not cpf.isdigit():
            return jsonify({'valido': False, 'message': 'CPF deve ter 11 dígitos numéricos'})
        
        # Verificar se todos os dígitos são iguais
        if cpf == cpf[0] * 11:
            return jsonify({'valido': False, 'message': 'CPF inválido'})
        
        # Algoritmo de validação do CPF
        def calcular_digito(cpf_parcial, pesos):
            soma = sum(int(cpf_parcial[i]) * pesos[i] for i in range(len(cpf_parcial)))
            resto = soma % 11
            return 0 if resto < 2 else 11 - resto
        
        # Verificar primeiro dígito
        primeiro_digito = calcular_digito(cpf[:9], [10, 9, 8, 7, 6, 5, 4, 3, 2])
        if int(cpf[9]) != primeiro_digito:
            return jsonify({'valido': False, 'message': 'CPF inválido'})
        
        # Verificar segundo dígito
        segundo_digito = calcular_digito(cpf[:10], [11, 10, 9, 8, 7, 6, 5, 4, 3, 2])
        if int(cpf[10]) != segundo_digito:
            return jsonify({'valido': False, 'message': 'CPF inválido'})
        
        return jsonify({'valido': True, 'message': 'CPF válido'})
        
    except Exception as e:
        print(f"Erro ao validar CPF: {e}")
        return jsonify({'valido': False, 'error': 'Erro interno do servidor'})

@app.route('/certificado200k_buscar_por_nome', methods=['POST'])
def certificado200k_buscar_por_nome():
    """Busca atletas por nome (para administração)"""
    try:
        data = request.get_json()
        nome = data.get('nome', '').strip()
        
        if len(nome) < 3:
            return jsonify({'success': False, 'message': 'Nome deve ter pelo menos 3 caracteres'})
        
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT IDATLETA, CONCAT(NOME, ' ', SOBRENOME) AS NOME_COMPLETO,
                   CPF, DATANASC
            FROM ATLETA 
            WHERE CONCAT(NOME, ' ', SOBRENOME) LIKE %s
            ORDER BY NOME, SOBRENOME
            LIMIT 20
        """, (f'%{nome}%',))
        
        atletas = cur.fetchall()
        cur.close()
        
        resultado = []
        for atleta in atletas:
            resultado.append({
                'idatleta': atleta[0],
                'nome': atleta[1],
                'cpf': atleta[2],
                'datanasc': atleta[3].strftime('%Y-%m-%d') if atleta[3] else None
            })
        
        return jsonify({
            'success': True,
            'atletas': resultado
        })
        
    except Exception as e:
        print(f"Erro ao buscar por nome: {e}")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'})


@app.route('/relatorio200k_listar_finalizadores')
def relatorio200k_listar_finalizadores():
    """Lista todos os atletas que completaram a prova"""
    try:
        cur = mysql.connection.cursor()
        
        # Atletas que completaram solo
        cur.execute("""
            SELECT CONCAT(i.NUPEITO,' - ', a.NOME, ' ', a.SOBRENOME) AS NOME, a.SEXO, 'SOLO' AS EQUIPE,
                   200 AS KM_PERCORRIDO,
                   SEC_TO_TIME(TIMESTAMPDIFF(SECOND, 
                     (SELECT DATA_HORA FROM PROVA_PARCIAIS_200K WHERE KM = 0 AND IDATLETA = a.IDATLETA), 
                     (SELECT DATA_HORA FROM PROVA_PARCIAIS_200K WHERE KM = 200 AND IDATLETA = a.IDATLETA))) AS TEMPO_TOTAL,
                     CONCAT(NOME, ' ',SOBRENOME) AS ORDER_NOME
            FROM ATLETA a, INSCRICAO i
            WHERE EXISTS (SELECT 1 FROM PROVA_PARCIAIS_200K WHERE IDEA = 0 AND KM = 200 AND IDATLETA = a.IDATLETA)
            AND i.IDATLETA = a.IDATLETA
            
            UNION ALL
            
            SELECT CONCAT(i.NUPEITO,' - ', a.NOME, ' ', a.SOBRENOME) AS NOME, a.SEXO,
            CONCAT(UPPER(em.DEREDUZ),' - ',e.NOME_EQUIPE) AS EQUIPE,
			   (ea.KM_FIM - ea.KM_INI) AS KM_PERCORRIDO,
			   SEC_TO_TIME(TIMESTAMPDIFF(SECOND, 
				 (SELECT DATA_HORA FROM PROVA_PARCIAIS_200K WHERE KM = ea.KM_INI AND IDEA = ea.IDEA), 
				 (SELECT DATA_HORA FROM PROVA_PARCIAIS_200K WHERE KM = ea.KM_FIM AND IDEA = ea.IDEA))) AS TEMPO_TOTAL,
				 CONCAT(NOME, ' ',SOBRENOME) AS ORDER_NOME
            FROM ATLETA a, INSCRICAO i, EQUIPE_ATLETAS ea, EQUIPE e, EVENTO_MODALIDADE em
            WHERE e.IDEA = ea.IDEA 
            AND ea.IDATLETA = a.IDATLETA
            AND em.IDITEM = i.IDITEM
            AND i.IDATLETA = a.IDATLETA
            AND EXISTS (SELECT 1 FROM PROVA_PARCIAIS_200K WHERE KM = ea.KM_FIM AND IDEA = ea.IDEA)
            
            ORDER BY ORDER_NOME
        """)
        
        finalizadores = cur.fetchall()
        cur.close()
        
        resultado = []
        for finalizador in finalizadores:
            resultado.append({
                'nome': finalizador[0],
		'sexo': finalizador[1],
                'equipe': finalizador[2],
                'km_percorrido': finalizador[3],
                'tempo_total': str(finalizador[4]) if finalizador[4] else None
            })
        # o ultimo campo ORDER_NOME não vou precisar, inclui na SQL apenas para ordenar por NOME

        return jsonify({
            'success': True,
            'finalizadores': resultado,
            'total': len(resultado)
        })
        
    except Exception as e:
        print(f"Erro ao listar finalizadores: {e}")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'})


@app.route('/relatorio200k_detalhes_atleta/<int:idatleta>')
def relatorio200k_detalhes_atleta(idatleta):
    """Obtém detalhes completos do atleta e sua participação"""
    try:
        cur = mysql.connection.cursor()
        
        # Dados básicos do atleta
        cur.execute("""
            SELECT IDATLETA, CONCAT(NOME, ' ', SOBRENOME) AS NOME_COMPLETO,
                   NOME, SOBRENOME, CPF, DATANASC
            FROM ATLETA 
            WHERE IDATLETA = %s
        """, (idatleta,))
        
        atleta = cur.fetchone()
        if not atleta:
            cur.close()
            return jsonify({'success': False, 'message': 'Atleta não encontrado'})
        
        # Verificar participação solo
        cur.execute("""
            SELECT KM, DATA_HORA 
            FROM PROVA_PARCIAIS_200K 
            WHERE IDATLETA = %s 
            ORDER BY KM
        """, (idatleta,))
        
        pontos_solo = cur.fetchall()
        
        # Verificar participação em equipe
        cur.execute("""
            SELECT ea.IDEA, ea.KM_INI, ea.KM_FIM,
                   p1.DATA_HORA as DATA_INICIO,
                   p2.DATA_HORA as DATA_FIM
            FROM EQUIPE_ATLETAS ea
            LEFT JOIN PROVA_PARCIAIS_200K p1 ON p1.IDEA = ea.IDEA AND p1.KM = ea.KM_INI
            LEFT JOIN PROVA_PARCIAIS_200K p2 ON p2.IDEA = ea.IDEA AND p2.KM = ea.KM_FIM
            WHERE ea.IDATLETA = %s
        """, (idatleta,))
        
        dados_equipe = cur.fetchone()
        cur.close()
        
        resultado = {
            'atleta': {
                'idatleta': atleta[0],
                'nome_completo': atleta[1],
                'nome': atleta[2],
                'sobrenome': atleta[3],
                'cpf': atleta[4],
                'datanasc': atleta[5].strftime('%Y-%m-%d') if atleta[5] else None
            },
            'participacao_solo': {
                'participou': len(pontos_solo) > 0,
                'completou': any(ponto[0] == 200 for ponto in pontos_solo),
                'pontos': [{'km': ponto[0], 'data_hora': ponto[1].strftime('%Y-%m-%d %H:%M:%S') if ponto[1] else None} for ponto in pontos_solo]
            },
            'participacao_equipe': {
                'participou': dados_equipe is not None,
                'completou': dados_equipe is not None and dados_equipe[4] is not None,
                'detalhes': {
                    'idea': dados_equipe[0] if dados_equipe else None,
                    'km_ini': dados_equipe[1] if dados_equipe else None,
                    'km_fim': dados_equipe[2] if dados_equipe else None,
                    'data_inicio': dados_equipe[3].strftime('%Y-%m-%d %H:%M:%S') if dados_equipe and dados_equipe[3] else None,
                    'data_fim': dados_equipe[4].strftime('%Y-%m-%d %H:%M:%S') if dados_equipe and dados_equipe[4] else None,
                    'distancia': dados_equipe[2] - dados_equipe[1] if dados_equipe and dados_equipe[1] and dados_equipe[2] else None
                } if dados_equipe else None
            }
        }
        
        return jsonify({
            'success': True,
            'dados': resultado
        })
        
    except Exception as e:
        print(f"Erro ao obter detalhes do atleta: {e}")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'})

@app.route('/relatorio200k_ranking_solo')
def certificado200k_ranking_solo():
    """Obtém ranking dos atletas na modalidade solo"""
    try:
        cur = mysql.connection.cursor()
        
        cur.execute("""
            SELECT 
            CONCAT(i.NUPEITO,' - ',a.NOME, ' ', a.SOBRENOME) AS NOME,
            a.SEXO,
            TIME_FORMAT(
                SEC_TO_TIME(
                TIMESTAMPDIFF(
                    SECOND, 
                    (SELECT DATA_HORA FROM PROVA_PARCIAIS_200K WHERE KM = 0 AND IDATLETA = a.IDATLETA),
                    (SELECT DATA_HORA FROM PROVA_PARCIAIS_200K WHERE KM = 200 AND IDATLETA = a.IDATLETA)
                )
                ), '%H:%i'
            ) AS TEMPO_TOTAL,
            (SELECT DATA_HORA FROM PROVA_PARCIAIS_200K WHERE KM = 0 AND IDATLETA = a.IDATLETA) AS DATA_LARGADA,
            (SELECT DATA_HORA FROM PROVA_PARCIAIS_200K WHERE KM = 200 AND IDATLETA = a.IDATLETA) AS DATA_CHEGADA
            FROM ATLETA a, INSCRICAO i
            WHERE i.IDITEM = 1
            AND i.IDATLETA = a.IDATLETA
            AND EXISTS (SELECT 1 FROM PROVA_PARCIAIS_200K WHERE KM = 200 AND IDATLETA = a.IDATLETA)
            ORDER BY TIMESTAMPDIFF(
            SECOND, 
            (SELECT DATA_HORA FROM PROVA_PARCIAIS_200K WHERE KM = 0 AND IDATLETA = a.IDATLETA),
            (SELECT DATA_HORA FROM PROVA_PARCIAIS_200K WHERE KM = 200 AND IDATLETA = a.IDATLETA)
            )
        """)
        
        ranking = cur.fetchall()
        cur.close()
        
        resultado = []
        for posicao, atleta in enumerate(ranking, 1):
            resultado.append({
                'posicao': posicao,
                'nome': atleta[0],
		'sexo': atleta[1],
                'tempo_total': str(atleta[2]) if atleta[2] else None,
                'data_largada': atleta[3].strftime('%Y-%m-%d %H:%M:%S') if atleta[3] else None,
                'data_chegada': atleta[4].strftime('%Y-%m-%d %H:%M:%S') if atleta[4] else None
            })
        
        return jsonify({
            'success': True,
            'ranking': resultado,
            'total': len(resultado)
        })
        
    except Exception as e:
        print(f"Erro ao obter ranking solo: {e}")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'})

@app.route('/relatorio200k_ranking_equipe')
def certificado200k_ranking_equipe():
    """Obtém ranking dos atletas na modalidade equipe"""
    try:
        cur = mysql.connection.cursor()
        
        cur.execute("""
            SELECT CONCAT(i.NUPEITO,' - ',a.NOME, ' ', a.SOBRENOME) AS NOME, a.SEXO,
                   CASE 
                     WHEN (ea.KM_FIM - ea.KM_INI) = 100 THEN 'DUPLA'
                     WHEN (ea.KM_FIM - ea.KM_INI) = 50 THEN 'QUARTETO'
                     WHEN (ea.KM_FIM - ea.KM_INI) = 25 THEN 'OCTETO'
                     ELSE 'EQUIPE'
                   END AS MODALIDADE,
                   (ea.KM_FIM - ea.KM_INI) AS KM_PERCORRIDO,
                   SEC_TO_TIME(TIMESTAMPDIFF(SECOND, 
                     (SELECT DATA_HORA FROM PROVA_PARCIAIS_200K WHERE KM = ea.KM_INI AND IDEA = ea.IDEA), 
                     (SELECT DATA_HORA FROM PROVA_PARCIAIS_200K WHERE KM = ea.KM_FIM AND IDEA = ea.IDEA))) AS TEMPO_TOTAL,
                   (SELECT DATA_HORA FROM PROVA_PARCIAIS_200K WHERE KM = ea.KM_INI AND IDEA = ea.IDEA) AS DATA_LARGADA,
                   (SELECT DATA_HORA FROM PROVA_PARCIAIS_200K WHERE KM = ea.KM_FIM AND IDEA = ea.IDEA) AS DATA_CHEGADA,
                   ea.IDEA
            FROM ATLETA a, INSCRICAO i, EQUIPE_ATLETAS ea
            WHERE ea.IDATLETA = a.IDATLETA
            AND i.IDATLETA = a.IDATLETA
            AND EXISTS (SELECT 1 FROM PROVA_PARCIAIS_200K WHERE KM = ea.KM_FIM AND IDEA = ea.IDEA)
            ORDER BY MODALIDADE, TIMESTAMPDIFF(SECOND, 
              (SELECT DATA_HORA FROM PROVA_PARCIAIS_200K WHERE KM = ea.KM_INI AND IDEA = ea.IDEA), 
              (SELECT DATA_HORA FROM PROVA_PARCIAIS_200K WHERE KM = ea.KM_FIM AND IDEA = ea.IDEA))
        """)
        
        ranking = cur.fetchall()
        cur.close()
        
        # Agrupar por modalidade
        resultado = {'DUPLA': [], 'QUARTETO': [], 'OCTETO': []}
        contadores = {'DUPLA': 1, 'QUARTETO': 1, 'OCTETO': 1}
        
        for atleta in ranking:
            modalidade = atleta[2]
            if modalidade in resultado:
                resultado[modalidade].append({
                    'posicao': contadores[modalidade],
                    'nome': atleta[0],
                    'sexo': atleta[1],  # CORREÇÃO: linha corrigida
                    'km_percorrido': atleta[3],
                    'tempo_total': str(atleta[4]) if atleta[4] else None,
                    'data_largada': atleta[5].strftime('%Y-%m-%d %H:%M:%S') if atleta[5] else None,
                    'data_chegada': atleta[6].strftime('%Y-%m-%d %H:%M:%S') if atleta[6] else None,
                    'idea': atleta[7]
                })
                contadores[modalidade] += 1
        
        return jsonify({
            'success': True,
            'ranking': resultado,
            'total': {
                'dupla': len(resultado['DUPLA']),
                'quarteto': len(resultado['QUARTETO']),
                'octeto': len(resultado['OCTETO'])
            }
        })
        
    except Exception as e:
        print(f"Erro ao obter ranking equipe: {e}")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'})

@app.route('/relatorio200k_equipes')
def relatorio200k_equipes():
    """Lista todas as equipes e seus membros"""
    try:
        cur = mysql.connection.cursor()
        
        cur.execute("""
            SELECT DISTINCT ea.IDEA, e.NOME_EQUIPE,
                   CASE 
                     WHEN COUNT(ea.IDATLETA) = 2 THEN 'DUPLA'
                     WHEN COUNT(ea.IDATLETA) = 4 THEN 'QUARTETO'
                     WHEN COUNT(ea.IDATLETA) = 8 THEN 'OCTETO'
                     ELSE 'EQUIPE'
                   END AS MODALIDADE,
                   COUNT(ea.IDATLETA) AS TOTAL_ATLETAS,
                   (SELECT DATA_HORA FROM PROVA_PARCIAIS_200K WHERE KM = 0 AND IDEA = e.IDEA) AS DATA_HORA_LARGADA,
                   (SELECT DATA_HORA FROM PROVA_PARCIAIS_200K WHERE KM = 200 AND IDEA = e.IDEA) AS DATA_HORA_CHEGADA
            FROM EQUIPE_ATLETAS ea, EQUIPE e
            WHERE ea.IDEA = e.IDEA
            GROUP BY ea.IDEA
            ORDER BY ea.IDEA
        """)
        
        equipes = cur.fetchall()
        
        resultado = []
        for equipe in equipes:
            idea = equipe[0]
            nome_equipe = equipe[1]
            modalidade = equipe[2]
            total_atletas = equipe[3]
            datahora_largada = equipe[4]
            datahora_chegada = equipe[5]

            # Buscar membros da equipe
            cur.execute("""
                SELECT CONCAT(i.NUPEITO,' - ',a.NOME, ' ', a.SOBRENOME) AS NOME, a.SEXO,
                       CONCAT(ea.KM_INI,' - ',ea.KM_FIM) AS PARCIAL,
                       (ea.KM_FIM - ea.KM_INI) AS KM_PERCORRIDO,
                       (SELECT DATA_HORA FROM PROVA_PARCIAIS_200K WHERE KM = ea.KM_FIM AND IDEA = ea.IDEA) AS DATA_HORA_CHEGADA,
                       SEC_TO_TIME(TIMESTAMPDIFF(SECOND, 
                         (SELECT DATA_HORA FROM PROVA_PARCIAIS_200K WHERE KM = ea.KM_INI AND IDEA = ea.IDEA), 
                         (SELECT DATA_HORA FROM PROVA_PARCIAIS_200K WHERE KM = ea.KM_FIM AND IDEA = ea.IDEA))) AS TEMPO_INDIVIDUAL,
                       EXISTS (SELECT 1 FROM PROVA_PARCIAIS_200K WHERE KM = ea.KM_FIM AND IDEA = ea.IDEA) AS COMPLETOU
                FROM ATLETA a, INSCRICAO i, EQUIPE_ATLETAS ea
                WHERE ea.IDATLETA = a.IDATLETA 
                AND i.IDATLETA = a.IDATLETA 
                AND ea.IDEA = %s
                ORDER BY ea.KM_INI
            """, (idea,))
            
            membros = cur.fetchall()
            
            # Verificar se a equipe completou (todos os membros terminaram)
            equipe_completou = all(membro[5] for membro in membros)
            
            # Calcular tempo total da equipe (do primeiro ao último)
            tempo_total_equipe = None
            if equipe_completou:
                cur.execute("""
                    SELECT SEC_TO_TIME(TIMESTAMPDIFF(SECOND,
                        (SELECT MIN(DATA_HORA) FROM PROVA_PARCIAIS_200K WHERE IDEA = %s AND KM = 0),
                        (SELECT MAX(DATA_HORA) FROM PROVA_PARCIAIS_200K WHERE IDEA = %s AND KM = 200)
                    )) AS TEMPO_TOTAL
                """, (idea, idea))
                tempo_result = cur.fetchone()
                tempo_total_equipe = str(tempo_result[0]) if tempo_result and tempo_result[0] else None
            
            resultado.append({
                'idea': idea,
                'nome_equipe': nome_equipe,
                'modalidade': modalidade,
                'total_atletas': total_atletas,
                'datahora_largada': datahora_largada.strftime('%d/%m/%Y %H:%M') if datahora_largada else None,
                'datahora_chegada': datahora_chegada.strftime('%d/%m/%Y %H:%M') if datahora_chegada else None,
                'completou': equipe_completou,
                'tempo_total': tempo_total_equipe,
                'membros': [{
                    'nome': membro[0],
		    'sexo': membro[1],
                    'parcial': membro[2],
                    'km_percorrido': membro[3],
                    'chegada_parcial': membro[4].strftime('%d/%m/%Y %H:%M') if membro[4] else None,
                    'tempo_individual': str(membro[5]) if membro[5] else None,
                    'completou': membro[6]
                } for membro in membros]
                
            })
        
        cur.close()
        
        return jsonify({
            'success': True,
            'equipes': resultado,
            'total': len(resultado)
        })
        
    except Exception as e:
        print(f"Erro ao listar equipes: {e}")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'})
	    

@app.route('/certificado200k_relatorio_geral')
def certificado200k_relatorio_geral():
    """Gera relatório geral da prova"""
    try:
        cur = mysql.connection.cursor()
        
        # Estatísticas gerais
        cur.execute("SELECT COUNT(*) FROM INSCRICAO")
        total_atletas = cur.fetchone()[0]
        
        cur.execute("""
            SELECT COUNT(DISTINCT IDATLETA) 
            FROM PROVA_PARCIAIS_200K 
            WHERE IDEA = 0 AND KM = 200
        """)
        completaram_solo = cur.fetchone()[0]
        
        cur.execute("""
            SELECT COUNT(DISTINCT ea.IDATLETA) 
            FROM EQUIPE_ATLETAS ea
            JOIN PROVA_PARCIAIS_200K p ON p.IDEA = ea.IDEA AND p.KM = ea.KM_FIM
        """)
        completaram_equipe = cur.fetchone()[0]
        
        # Estatísticas por modalidade
        cur.execute("""
            SELECT 
                CASE 
                    WHEN (ea.KM_FIM - ea.KM_INI) = 100 THEN 'DUPLA'
                    WHEN (ea.KM_FIM - ea.KM_INI) = 50 THEN 'QUARTETO'
                    WHEN (ea.KM_FIM - ea.KM_INI) = 25 THEN 'OCTETO'
                    ELSE 'EQUIPE'
                END AS MODALIDADE,
                COUNT(DISTINCT ea.IDATLETA) AS TOTAL_ATLETAS,
                COUNT(DISTINCT CASE WHEN p.KM = ea.KM_FIM THEN ea.IDATLETA END) AS COMPLETARAM
            FROM EQUIPE_ATLETAS ea
            LEFT JOIN PROVA_PARCIAIS_200K p ON p.IDEA = ea.IDEA AND p.KM = ea.KM_FIM
            GROUP BY MODALIDADE
        """)
        
        stats_equipe = cur.fetchall()
        
        # Tempos por modalidade
        cur.execute("""
            SELECT 'SOLO' AS MODALIDADE,
                   MIN(SEC_TO_TIME(TIMESTAMPDIFF(SECOND, 
                     (SELECT DATA_HORA FROM PROVA_PARCIAIS_200K WHERE KM = 0 AND IDATLETA = a.IDATLETA), 
                     (SELECT DATA_HORA FROM PROVA_PARCIAIS_200K WHERE KM = 200 AND IDATLETA = a.IDATLETA)))) AS MELHOR_TEMPO,
                   MAX(SEC_TO_TIME(TIMESTAMPDIFF(SECOND, 
                     (SELECT DATA_HORA FROM PROVA_PARCIAIS_200K WHERE KM = 0 AND IDATLETA = a.IDATLETA), 
                     (SELECT DATA_HORA FROM PROVA_PARCIAIS_200K WHERE KM = 200 AND IDATLETA = a.IDATLETA)))) AS PIOR_TEMPO,
                   AVG(TIMESTAMPDIFF(SECOND, 
                     (SELECT DATA_HORA FROM PROVA_PARCIAIS_200K WHERE KM = 0 AND IDATLETA = a.IDATLETA), 
                     (SELECT DATA_HORA FROM PROVA_PARCIAIS_200K WHERE KM = 200 AND IDATLETA = a.IDATLETA))) AS TEMPO_MEDIO_SEGUNDOS
            FROM ATLETA a
            WHERE EXISTS (SELECT 1 FROM PROVA_PARCIAIS_200K WHERE KM = 200 AND IDATLETA = a.IDATLETA)
        """)
        
        stats_solo = cur.fetchone()
        
        cur.close()
        
        # Formatar estatísticas de equipe
        stats_equipe_formatadas = {}
        for stat in stats_equipe:
            stats_equipe_formatadas[stat[0]] = {
                'total_atletas': stat[1],
                'completaram': stat[2],
                'taxa_conclusao': round((stat[2] / stat[1]) * 100, 2) if stat[1] > 0 else 0
            }
        
        # Calcular tempo médio em formato legível
        tempo_medio_legivel = None
        if stats_solo and stats_solo[3]:
            segundos = int(stats_solo[3])
            horas = segundos // 3600
            minutos = (segundos % 3600) // 60
            segundos = segundos % 60
            tempo_medio_legivel = f"{horas:02d}:{minutos:02d}:{segundos:02d}"
        
        resultado = {
            'resumo_geral': {
                'total_atletas': total_atletas,
                'completaram_solo': completaram_solo,
                'completaram_equipe': completaram_equipe,
                'total_completaram': completaram_solo + completaram_equipe,
                'taxa_conclusao_geral': round(((completaram_solo + completaram_equipe) / total_atletas) * 100, 2) if total_atletas > 0 else 0
            },
            'modalidade_solo': {
                'completaram': completaram_solo,
                'melhor_tempo': str(stats_solo[1]) if stats_solo and stats_solo[1] else None,
                'pior_tempo': str(stats_solo[2]) if stats_solo and stats_solo[2] else None,
                'tempo_medio': tempo_medio_legivel
            },
            'modalidades_equipe': stats_equipe_formatadas,
            'data_relatorio': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return jsonify({
            'success': True,
            'relatorio': resultado
        })
        
    except Exception as e:
        print(f"Erro ao gerar relatório geral: {e}")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'})

# Funções auxiliares para validação
def validar_cpf(cpf):
    """Valida CPF usando algoritmo padrão"""
    if not cpf or len(cpf) != 11 or not cpf.isdigit():
        return False
    
    # Verificar se todos os dígitos são iguais
    if cpf == cpf[0] * 11:
        return False
    
    # Algoritmo de validação do CPF
    def calcular_digito(cpf_parcial, pesos):
        soma = sum(int(cpf_parcial[i]) * pesos[i] for i in range(len(cpf_parcial)))
        resto = soma % 11
        return 0 if resto < 2 else 11 - resto
    
    # Verificar primeiro dígito
    primeiro_digito = calcular_digito(cpf[:9], [10, 9, 8, 7, 6, 5, 4, 3, 2])
    if int(cpf[9]) != primeiro_digito:
        return False
    
    # Verificar segundo dígito
    segundo_digito = calcular_digito(cpf[:10], [11, 10, 9, 8, 7, 6, 5, 4, 3, 2])
    if int(cpf[10]) != segundo_digito:
        return False
    
    return True

def formatar_tempo(segundos):
    """Formata tempo em segundos para HH:MM:SS"""
    if not segundos:
        return None
    
    horas = int(segundos // 3600)
    minutos = int((segundos % 3600) // 60)
    segundos = int(segundos % 60)
    return f"{horas:02d}:{minutos:02d}:{segundos:02d}"

def limpar_cpf(cpf):
    """Remove formatação do CPF"""
    if not cpf:
        return ''
    return cpf.replace('.', '').replace('-', '').replace(' ', '')

# Middleware para log de requests (opcional)
@app.before_request
def log_request_info():
    """Log das requisições para debug"""
    if request.endpoint and request.endpoint.startswith('certificado200k_'):
        print(f"Certificado 200K - {request.method} {request.endpoint} - IP: {request.remote_addr}")

# Error handlers específicos para as rotas de certificado
@app.errorhandler(500)
def handle_500(e):
    if request.endpoint and request.endpoint.startswith('certificado200k_'):
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500
    return e

@app.errorhandler(404)
def handle_404(e):
    if request.endpoint and request.endpoint.startswith('certificado200k_'):
        return jsonify({'success': False, 'error': 'Endpoint não encontrado'}), 404
    return e

#### RELATORIOS 200K #####################

@app.route('/relatorios200k')
def relatorios200k():
    """Página principal dos relatórios"""
    return render_template('relatorios200k.html')

@app.route('/relatorio_finalizadores')
def relatorio200k_finalizadores():
    """Página do relatório de finalizadores"""
    return render_template('relatorio_finalizadores.html')

@app.route('/relatorio_ranking_solo')
def relatorio200k_ranking_solo():
    """Página do relatório de ranking solo"""
    return render_template('relatorio_ranking_solo.html')

@app.route('/relatorio_ranking_equipe')
def relatorio200k_ranking_equipe():
    """Página do relatório de ranking de equipe"""
    return render_template('relatorio_ranking_equipe.html')

@app.route('/relatorio_equipes')
def relatorio_equipes():
    """Página do relatório de equipes detalhadas"""
    return render_template('relatorio_equipes.html')

@app.route('/relatorio_geral')
def relatorio_geral():
    """Página do relatório geral"""
    return render_template('relatorio_geral.html')

# Rota adicional para exportação PDF (opcional)
@app.route('/exportar_relatorio_pdf/<tipo>')
def exportar_relatorio_pdf(tipo):
    """Exporta relatório específico em PDF"""
    try:
        # Mapear tipos de relatório para templates
        templates = {
            'finalizadores': 'relatorio_finalizadores.html',
            'ranking_solo': 'relatorio_ranking_solo.html',
            'ranking_equipe': 'relatorio_ranking_equipe.html',
            'equipes': 'relatorio_equipes.html',
            'geral': 'relatorio_geral.html'
        }
        
        if tipo not in templates:
            return jsonify({'success': False, 'error': 'Tipo de relatório inválido'})
        
        # Renderizar template HTML
        html_content = render_template(templates[tipo])
        
        # Configurações para PDF
        options = {
            'page-size': 'A4',
            'orientation': 'Portrait',
            'margin-top': '20mm',
            'margin-right': '20mm',
            'margin-bottom': '20mm',
            'margin-left': '20mm',
            'encoding': 'UTF-8',
            'no-outline': None,
            'enable-local-file-access': None
        }
        
        # Gerar PDF
        pdf = pdfkit.from_string(html_content, False, options=options)
        
        # Criar resposta
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=relatorio_{tipo}_200k.pdf'
        
        return response
        
    except Exception as e:
        print(f"Erro ao exportar PDF: {e}")
        return jsonify({'success': False, 'error': 'Erro ao gerar PDF'})

# Rota para buscar dados de atleta específico (se necessário)
@app.route('/atleta_detalhes/<int:idatleta>')
def atleta_detalhes(idatleta):
    """Redireciona para a rota existente de detalhes do atleta"""
    return redirect(f'/relatorio200k_detalhes_atleta/{idatleta}')


@app.route('/arealslope')
def arealslope():
    """
    Redirecionamento permanente da página antiga para a nova estrutura dinâmica
    Rota antiga: /arealslope
    Nova rota: /evento/arealslope
    """
    # Redirecionamento 301 (permanente) - melhor para SEO
    return redirect(url_for('visualizar_evento', dslink='arealslope'), code=301)



@app.route('/macaxeirabackyard')
def backyard():
    """
    Redirecionamento permanente da página antiga para a nova estrutura dinâmica
    Rota antiga: /arealslope
    Nova rota: /evento/arealslope
    """
    # Redirecionamento 301 (permanente) - melhor para SEO
    return redirect(url_for('visualizar_evento', dslink='macaxeirabackyard'), code=301)

############################

@app.route('/api/lote-inscricao/<int:iditem>')
def get_lote_inscricao(iditem):
    """API para obter dados de um lote específico para inscrição"""
    try:
        cur = mysql.connection.cursor()
        
        cur.execute("""
            SELECT 
              ei.IDITEM, 
              ei.DESCRICAO, 
              ei.VLINSCRICAO, 
              ROUND((ei.VLINSCRICAO * ei.PCTAXA / 100), 2) AS VLTAXA,
              ROUND(ei.VLINSCRICAO + (ei.VLINSCRICAO * ei.PCTAXA / 100), 2) AS VLTOTAL,
              (SELECT ROUND((VLINSCRICAO / 2), 2) FROM EVENTO_ITENS WHERE IDITEM = ei.IDITEM_ULTIMO_LOTE) AS VL_MEIA,
              (SELECT ROUND(((VLINSCRICAO / 2) * PCTAXA / 100), 2) FROM EVENTO_ITENS WHERE IDITEM = ei.IDITEM_ULTIMO_LOTE) AS VL_TAXA_MEIA,
              (SELECT ROUND((VLINSCRICAO / 2) + ((VLINSCRICAO / 2) * PCTAXA / 100), 2) FROM EVENTO_ITENS WHERE IDITEM = ei.IDITEM_ULTIMO_LOTE) AS VL_TOTAL_MEIA,
              e.DESCRICAO AS TITULO, e.IDEVENTO
            FROM EVENTO_ITENS ei
            JOIN EVENTO_1 e ON ei.IDEVENTO = e.IDEVENTO
            WHERE ei.IDITEM = %s
        """, (iditem,))
        
        lote_data = cur.fetchone()
        cur.close()
        
        if not lote_data:
            return jsonify({'error': 'Lote não encontrado'}), 404
        
        # Função para formatar valores em formato brasileiro (para uso na API também)
        def formatar_valor_brasileiro_api(valor):
            """Converte valor decimal para formato brasileiro (vírgula como separador decimal)"""
            if valor is None:
                return "0,00"
            return f"{float(valor):.2f}".replace('.', ',')
        
        return jsonify({
            'idevento': lote_data[9],
            'iditem': lote_data[0],
            'titulo': lote_data[8],
            'descricao': lote_data[1],
            'vlinscricao': float(lote_data[2]),
            'vltaxa': float(lote_data[3]),
            'vltotal': float(lote_data[4]),
            'vlinscricao_meia': float(lote_data[5]),
            'vltaxa_meia': float(lote_data[6]),
            'vltotal_meia': float(lote_data[7]),
            # Valores formatados em padrão brasileiro para exibição
            'vlinscricao_formatada': formatar_valor_brasileiro_api(lote_data[2]),
            'vltaxa_formatada': formatar_valor_brasileiro_api(lote_data[3]),
            'vltotal_formatada': formatar_valor_brasileiro_api(lote_data[4]),
            'vlinscricao_meia_formatada': formatar_valor_brasileiro_api(lote_data[5]),
            'vltaxa_meia_formatada': formatar_valor_brasileiro_api(lote_data[6]),
            'vltotal_meia_formatada': formatar_valor_brasileiro_api(lote_data[7])
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro ao buscar dados do lote: {str(e)}'}), 500

#### INSCRIÇAO EVENTO ##########



@app.route('/evento_salvar_inscricao', methods=['POST'])
def evento_salvar_inscricao():
    try:
        dados = request.get_json()
        
        # Validações básicas
        if not dados:
            return jsonify({
                'success': False,
                'mensagem': 'Dados não fornecidos'
            }), 400
        
        # Campos obrigatórios
        campos_obrigatorios = [
            'email', 'cpf', 'nome', 'sobrenome', 'dtnascimento', 
            'idade', 'celular', 'sexo', 'camiseta', 'id_cidade', 'formapgto'
        ]
        
        for campo in campos_obrigatorios:
            if not dados.get(campo):
                return jsonify({
                    'success': False,
                    'mensagem': f'Campo {campo} é obrigatório'
                }), 400
        
        cursor = mysql.connection.cursor()
        
        # Verificar se existe inscrição pendente para exclusão
        cursor.execute("""
            SELECT IDINSCRICAO 
            FROM EVENTO_INSCRICAO 
            WHERE CPF = %s AND IDEVENTO = %s AND STATUS = 'P'
        """, (dados['cpf'], dados.get('idevento'),))
        
        inscricao_pendente = cursor.fetchone()
        
        # Se existe inscrição pendente, excluir antes de inserir nova
        if inscricao_pendente:
            cursor.execute("""
                DELETE FROM EVENTO_INSCRICAO 
                WHERE IDINSCRICAO = %s
            """, (inscricao_pendente[0],))
        
        # Verificar se CPF já está aprovado neste evento
        cursor.execute("""
            SELECT IDINSCRICAO 
            FROM EVENTO_INSCRICAO 
            WHERE CPF = %s AND IDEVENTO = %s AND STATUS = 'A'
        """, (dados['cpf'], dados.get('idevento'),))
        
        if cursor.fetchone():
            cursor.close()
            return jsonify({
                'success': False,
                'mensagem': 'CPF já inscrito neste evento'
            }), 400
        
        # Converter data de nascimento para formato MySQL
        data_nasc_str = dados['dtnascimento']  # dd/mm/yyyy
        dia, mes, ano = data_nasc_str.split('/')
        data_nasc_mysql = f"{ano}-{mes}-{dia}"  # yyyy-mm-dd
                
        data_e_hora_atual = datetime.now()
        fuso_horario = timezone('America/Manaus')
        data_inscricao = data_e_hora_atual.astimezone(fuso_horario)
        
        # INSERT nova inscrição (sempre)
        sql_insert = """
            INSERT INTO EVENTO_INSCRICAO (
                IDEVENTO, IDITEMEVENTO, IDLOTE, EMAIL, CPF, NOME, SOBRENOME, 
                DTNASCIMENTO, IDADE, CELULAR, SEXO, EQUIPE, CAMISETA,
                TEL_EMERGENCIA, CONT_EMERGENCIA, ESTADO, ID_CIDADE, 
                DATANASC, DTINSCRICAO, VLINSCRICAO, VLTAXA, VLTOTAL,
                FORMAPGTO, CUPOM, STATUS, FLEMAIL, NOME_PEITO
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """
        
        valores = (
            dados.get('idevento', 1),
            dados['iditemevento'],
            dados['idlote'],
            dados['email'],
            dados['cpf'],
            dados['nome'],
            dados['sobrenome'],
            dados['dtnascimento'],
            dados['idade'],
            dados['celular'],
            dados['sexo'],
            dados.get('equipe'),
            dados['camiseta'],
            dados.get('tel_emergencia'),
            dados.get('cont_emergencia'),
            dados['estado'],
            dados['id_cidade'],
            data_nasc_mysql,
            data_inscricao,
            dados['vlinscricao'],
            dados['vltaxa'],
            dados['vltotal'],
            dados['formapgto'],
            dados.get('cupom'),
            dados.get('status', 'P'),
            'N',
            dados['nomepeito']
        )
        
        cursor.execute(sql_insert, valores)
        inscricao_id = cursor.lastrowid
        
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({
            'success': True,
            'inscricao_id': inscricao_id,
            'mensagem': 'Inscrição salva com sucesso',
            'is_update': bool(inscricao_pendente)  # Mantido para compatibilidade
        })
        
    except Exception as e:
        app.logger.error(f"Erro ao salvar inscrição: {e}")
        return jsonify({
            'success': False,
            'mensagem': 'Erro interno do servidor'
        }), 500
    

@app.route('/api/lote-inscricao/<int:iditem>')
def api_lote_inscricao(iditem):
    """API para retornar dados do lote para inscrição"""
    try:
        cursor = mysql.connection.cursor()
        
        cursor.execute("""
            SELECT 
                ei.IDITEM,
                ei.DESCRICAO,
                ei.VLINSCRICAO,
                ROUND((ei.VLINSCRICAO * ei.PCTAXA / 100), 2) AS VLTAXA,
                ROUND(ei.VLINSCRICAO + (ei.VLINSCRICAO * ei.PCTAXA / 100), 2) AS VLTOTAL,
                (SELECT ROUND((VLINSCRICAO / 2), 2) FROM EVENTO_ITENS WHERE IDITEM = ei.IDITEM_ULTIMO_LOTE) AS VL_MEIA,
                (SELECT ROUND(((VLINSCRICAO / 2) * PCTAXA / 100), 2) FROM EVENTO_ITENS WHERE IDITEM = ei.IDITEM_ULTIMO_LOTE) AS VL_TAXA_MEIA,
                (SELECT ROUND((VLINSCRICAO / 2) + ((VLINSCRICAO / 2) * PCTAXA / 100), 2) FROM EVENTO_ITENS WHERE IDITEM = ei.IDITEM_ULTIMO_LOTE) AS VL_TOTAL_MEIA,
                ei.DELOTE,
                e.DESCRICAO AS TITULO
            FROM EVENTO_ITENS ei
            JOIN EVENTO_1 e ON ei.IDEVENTO = e.IDEVENTO
            WHERE ei.IDITEM = %s
        """, (iditem,))

        resultado = cursor.fetchone()
        cursor.close()
        
        if not resultado:
            return jsonify({
                'error': 'Lote não encontrado'
            }), 404
        
        return jsonify({
            'iditem': resultado[0],
            'descricao': resultado[1],
            'vlinscricao': float(resultado[2]) if resultado[2] else 0,
            'vltaxa': float(resultado[3]) if resultado[3] else 0,
            'vltotal': float(resultado[4]) if resultado[4] else 0,
            'vlinscricao_meia': float(resultado[5]) if resultado[5] else 0,
            'vltaxa_meia': float(resultado[6]) if resultado[6] else 0,
            'vltotal_meia': float(resultado[7]) if resultado[7] else 0,
            'delote': resultado[8],
            'evento_titulo': resultado[9]
        })
        
    except Exception as e:
        app.logger.error(f"Erro ao buscar dados do lote {iditem}: {e}")
        return jsonify({
            'error': 'Erro interno do servidor'
        }), 500


@app.route('/verifica-cpf-inscrito/<int:idevento>', methods=['GET'])
def verificar_cpf_inscrito(idevento):
    cpf = request.args.get('cpf', '')
    # Remove caracteres não numéricos
    cpf = ''.join(filter(str.isdigit, cpf))
    
    try:
        cur = mysql.connection.cursor()
        
        # Verificar se existe inscrição aprovada (STATUS = 'A')
        cur.execute("""
            SELECT 1 FROM EVENTO_INSCRICAO WHERE STATUS = 'A' AND CPF = %s AND IDEVENTO = %s
        """, (cpf, idevento))
        
        result_aprovado = cur.fetchone()
        
        # Verificar se existe inscrição pendente (STATUS = 'P')
        cur.execute("""
            SELECT IDINSCRICAO FROM EVENTO_INSCRICAO WHERE STATUS IN ('P','C','R') AND CPF = %s AND IDEVENTO = %s
        """, (cpf, idevento))
        
        result_pendente = cur.fetchone()
        cur.close()
        
        return jsonify({
            'exists': bool(result_aprovado),
            'has_pending': bool(result_pendente),
            'pending_id': result_pendente[0] if result_pendente else None
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/buscar-dados-cpf', methods=['GET'])
def buscar_dados_cpf():
    """Rota para buscar dados existentes do CPF"""
    try:
        cpf = request.args.get('cpf')
        print(f"DEBUG: CPF recebido: {cpf}")
        
        if not cpf:
            return jsonify({'success': False, 'message': 'CPF não fornecido'})
        
        cur = mysql.connection.cursor()
        print("DEBUG: Conexão com banco estabelecida")
        
        # SQL fornecida
        query = """
            SELECT CPF, NOME, SOBRENOME, EMAIL, DTNASCIMENTO, SEXO, ESTADO, 
            ID_CIDADE, CELULAR, TEL_EMERGENCIA, CONT_EMERGENCIA FROM PESSOA
            WHERE CPF = %s
        """

        print(f"DEBUG: Executando query com CPF: {cpf}")
        cur.execute(query, (cpf,))
        
        row = cur.fetchone()
        print(f"DEBUG: Resultado da query: {row}")
        
        cur.close()
        
        if row:
            # Tratar data de nascimento com segurança
            dtnascimento_formatada = None
            if row[4]:
                try:
                    if hasattr(row[4], 'strftime'):
                        dtnascimento_formatada = row[4].strftime('%d/%m/%Y')
                    else:
                        # Se for string, tentar converter
                        dtnascimento_formatada = str(row[4])
                except Exception as e:
                    print(f"DEBUG: Erro ao formatar data: {e}")
                    dtnascimento_formatada = None
            
            dados_retorno = {
                'success': True,
                'dados': {
                    'cpf': row[0],
                    'nome': row[1],
                    'sobrenome': row[2], 
                    'email': row[3],
                    'dtnascimento': dtnascimento_formatada,
                    'sexo': row[5],
                    'estado': row[6],
                    'id_cidade': row[7],
                    'celular': row[8],
                    'celular_emerg': row[9],
                    'contato_emerg': row[10]
                }
            }
            
            print(f"DEBUG: Dados de retorno: {dados_retorno}")
            return jsonify(dados_retorno)
        else:
            print("DEBUG: Nenhum dado encontrado")
            return jsonify({'success': False, 'message': 'Nenhum dado encontrado'})
    
    except Exception as e:
        print(f"DEBUG: Erro capturado: {str(e)}")
        print(f"DEBUG: Tipo do erro: {type(e)}")
        return jsonify({'success': False, 'error': f'Erro ao buscar dados: {str(e)}'}), 500


# Rota para exibir a página de consulta de inscrições
@app.route('/lista-eventos')
def lista_eventos():
    return render_template('lista_eventos.html')

# API para consultar inscrições por CPF e data de nascimento
@app.route('/api/minhas-inscricoes', methods=['POST'])
def get_minhas_inscricoes():
    try:
        cpf = request.form.get('cpf')
        data_nascimento = request.form.get('data_nascimento')
        
        # Validações básicas
        if not cpf or not data_nascimento:
            return jsonify({
                'success': False,
                'message': 'CPF e Data de Nascimento são obrigatórios'
            })
        
        # Remover formatação do CPF (manter apenas números)
        cpf_numeros = ''.join(filter(str.isdigit, cpf))
        
        if len(cpf_numeros) != 11:
            return jsonify({
                'success': False,
                'message': 'CPF deve conter 11 dígitos'
            })
        
        cursor = mysql.connection.cursor()
        query = """
            SELECT 
                e.TITULO, 
                e.ENDERECO, 
                CASE 
                    WHEN e.DATAINICIO = e.DATAFIM THEN CONCAT(e.DATAINICIO, ' ', e.HRINICIO)
                    ELSE CONCAT(e.DATAINICIO, ' ', e.HRINICIO, ' - ', e.DATAFIM)
                END AS DTEVENTO,
                CONCAT(ei.NOME, ' ', ei.SOBRENOME) AS NOME_COMPLETO,
                CASE WHEN i.KM = 0
                    THEN i.MODALIDADE
                    ELSE CONCAT(i.KM, ' KM') 
                END AS KM_DESCRICAO,  
                ei.VLINSCRICAO, 
                ei.VLTOTAL, 
                ei.FORMAPGTO,
                ei.IDPAGAMENTO, 
                ei.DTPAGAMENTO, 
                ei.FLEMAIL, 
                ei.IDINSCRICAO, 
                e.OBS, 
                e.DATAINICIO, 
                e.DATAFIM, 
                e.HRINICIO
            FROM EVENTO_INSCRICAO ei
            INNER JOIN EVENTO_ITEM i ON i.IDITEM = ei.IDITEMEVENTO
            INNER JOIN EVENTO1 e ON e.IDEVENTO = ei.IDEVENTO
            WHERE ei.STATUS = 'A'
              AND ei.DTNASCIMENTO = %s
              AND ei.CPF = %s
              AND e.DATAFIM >= CURDATE()
        """
        
        cursor.execute(query, (data_nascimento, cpf_numeros))
        inscricoes = cursor.fetchall()
        cursor.close()

        # Converter para lista de dicionários
        inscricoes_list = []
        for inscricao in inscricoes:
            # Os índices corretos baseados na query SELECT:
            # 0-TITULO, 1-ENDERECO, 2-DTEVENTO, 3-NOME_COMPLETO, 4-KM_DESCRICAO
            # 5-VLINSCRICAO, 6-VLTOTAL, 7-FORMAPGTO, 8-IDPAGAMENTO, 9-DTPAGAMENTO
            # 10-FLEMAIL, 11-IDINSCRICAO, 12-OBS, 13-DATAINICIO, 14-DATAFIM, 15-HRINICIO
            
            data_inicio = inscricao[13]
            data_fim = inscricao[14]
            hr_inicio = inscricao[15]

            # Formatar hora de início
            if hr_inicio:
                # Converter timedelta para string se necessário
                if hasattr(hr_inicio, 'total_seconds'):
                    # Se for timedelta, converter para HH:MM
                    total_seconds = int(hr_inicio.total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    hora_formatada = f"{hours:02d}:{minutes:02d}"
                else:
                    hora_formatada = str(hr_inicio)
            else:
                hora_formatada = ""

            # Formatar data do evento
            if hasattr(data_inicio, 'strftime') and hasattr(data_fim, 'strftime'):
                if data_inicio == data_fim:
                    # Mesmo dia
                    data_evento = f"{data_inicio.strftime('%d/%m/%Y')} {hora_formatada}".strip()
                else:
                    # Dias diferentes
                    data_evento = f"{data_inicio.strftime('%d/%m/%Y')} {hora_formatada} - {data_fim.strftime('%d/%m/%Y')}".strip()
            else:
                # Fallback se não for date/datetime
                data_evento = f"{data_inicio} {hora_formatada}".strip()

            # Formatar DTPAGAMENTO se for um objeto datetime
            dt_pagamento = inscricao[9]
            if dt_pagamento:
                if isinstance(dt_pagamento, datetime):
                    dt_pagamento_formatada = dt_pagamento.strftime('%d/%m/%Y %H:%M:%S')
                else:
                    # Se já for string, assumir que está no formato correto
                    dt_pagamento_formatada = str(dt_pagamento)
            else:
                dt_pagamento_formatada = ''
            
            inscricoes_list.append({
                'DESCRICAO': inscricao[0],
                'LOCAL': inscricao[1],
                'DTEVENTO': data_evento,
                'NOME_COMPLETO': inscricao[3],
                'KM_DESCRICAO': inscricao[4],
                'VLINSCRICAO': inscricao[5],
                'VLTOTAL': inscricao[6],
                'FORMAPGTO': inscricao[7],
                'IDPAGAMENTO': inscricao[8],
                'DTPAGAMENTO': dt_pagamento_formatada,
                'FLEMAIL': inscricao[10],
                'IDINSCRICAO': inscricao[11],
                'OBS': inscricao[12]
            })
        
        return jsonify({
            'success': True,
            'data': inscricoes_list,
            'total': len(inscricoes_list)
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'Erro interno do servidor',
            'error': str(e)
        }), 500

# Adicione esta nova rota ao seu Flask app:
@app.route('/lista-eventos-direto', methods=['POST'])
def lista_eventos_direto():
    try:
        cpf = request.form.get('cpf')
        data_nascimento = request.form.get('data_nascimento')
        
        # Validações básicas
        if not cpf or not data_nascimento:
            # Se não tiver os dados, redireciona para a página normal
            return redirect('/lista-eventos')
        
        # Remover formatação do CPF (manter apenas números)
        cpf_numeros = ''.join(filter(str.isdigit, cpf))
        
        if len(cpf_numeros) != 11:
            return redirect('/lista-eventos')
        
        # Buscar as inscrições diretamente
        cursor = mysql.connection.cursor()
        query = """
            SELECT 
                e.DESCRICAO, 
                e.LOCAL, 
                CASE 
                    WHEN e.DTINICIO = e.DTFIM THEN CONCAT(e.DTINICIO, ' ', e.HRINICIO)
                    ELSE CONCAT(e.DTINICIO, ' ', e.HRINICIO, ' - ', e.DTFIM)
                END AS DTEVENTO,
                CONCAT(ei.NOME, ' ', ei.SOBRENOME) AS NOME_COMPLETO,
                i.KM_DESCRICAO, 
                ei.VLINSCRICAO, 
                ei.VLTOTAL, 
                ei.FORMAPGTO,
                ei.IDPAGAMENTO, 
                ei.DTPAGAMENTO, 
                ei.FLEMAIL, 
                ei.IDINSCRICAO, 
                e.OBS
            FROM EVENTO_INSCRICAO ei
            INNER JOIN EVENTO_ITENS i ON i.IDITEM = ei.IDITEMEVENTO
            INNER JOIN EVENTO_1 e ON e.IDEVENTO = ei.IDEVENTO
            WHERE ei.STATUS = 'A'
              AND ei.DTNASCIMENTO = %s
              AND ei.CPF = %s
              AND STR_TO_DATE(e.DTFIM, '%%d/%%m/%%Y') >= CURDATE()
        """
        
        cursor.execute(query, (data_nascimento, cpf_numeros))
        inscricoes = cursor.fetchall()
        cursor.close()
        
        # Converter para lista de dicionários
        inscricoes_list = []
        for inscricao in inscricoes:
            # Formatar DTPAGAMENTO se for um objeto datetime
            dt_pagamento = inscricao[9]
            if dt_pagamento:
                if isinstance(dt_pagamento, datetime):
                    dt_pagamento_formatada = dt_pagamento.strftime('%d/%m/%Y %H:%M:%S')
                else:
                    dt_pagamento_formatada = str(dt_pagamento)
            else:
                dt_pagamento_formatada = ''
            
            inscricoes_list.append({
                'DESCRICAO': inscricao[0],
                'LOCAL': inscricao[1],
                'DTEVENTO': inscricao[2],
                'NOME_COMPLETO': inscricao[3],
                'KM_DESCRICAO': inscricao[4],
                'VLINSCRICAO': inscricao[5],
                'VLTOTAL': inscricao[6],
                'FORMAPGTO': inscricao[7],
                'IDPAGAMENTO': inscricao[8],
                'DTPAGAMENTO': dt_pagamento_formatada,
                'FLEMAIL': inscricao[10],
                'IDINSCRICAO': inscricao[11],
                'OBS': inscricao[12]
            })
        
        # Renderizar a página com os dados já carregados
        return render_template('lista_eventos.html', 
                             inscricoes_carregadas=True,
                             inscricoes=inscricoes_list,
                             total=len(inscricoes_list),
                             cpf=cpf,
                             data_nascimento=data_nascimento)
        
    except Exception as e:
        # Em caso de erro, redireciona para a página normal
        return redirect('/lista-eventos')



#### nova pagina evento ###########################

@app.route('/eventos')
def eventos_page():
    """Renderiza a página de cadastro de eventos"""
    return render_template('eventos.html')

@app.route('/api/auth', methods=['POST'])
def autenticar_admin():
    """API para autenticação administrativa"""
    try:
        data = request.get_json()
        senha_informada = data.get('senha', '').strip() if data else ''
        senha_adm = os.getenv('SENHA_ADM')
		
        # Debug - remover após testar
        print(f"Senha informada: '{senha_informada}'")
        print(f"Senha esperada: '{senha_adm}'")
        print(f"Senha ADM existe: {senha_adm is not None}")
        
        if not senha_adm:
            print("ERRO: Senha administrativa não configurada no ambiente")
            return jsonify({'error': 'Senha administrativa não configurada'}), 500
        
        if senha_informada == senha_adm:
            print("Autenticação bem-sucedida")
            return jsonify({
                'success': True,
                'message': 'Autenticado com sucesso'
            }), 200
        else:
            print("Senha incorreta")
            return jsonify({'error': 'Senha incorreta'}), 401
            
    except Exception as e:
        print(f"Erro na autenticação: {str(e)}")
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500


@app.route('/api/eventos', methods=['POST'])
def criar_evento():
    """API para criar um novo evento"""
    try:
        data = request.get_json()
        
        # Validação dos campos obrigatórios
        campos_obrigatorios = ['titulo', 'datainicio', 'datafim', 'dslink', 'idorganizador']
        for campo in campos_obrigatorios:
            if not data.get(campo):
                return jsonify({'error': f'Campo {campo} é obrigatório'}), 400
        
        # Validação e limpeza do dslink
        dslink = data.get('dslink', '').lower()
        dslink = re.sub(r'[^a-z0-9-]', '', dslink)
        
        if not dslink:
            return jsonify({'error': 'Link do evento deve conter apenas letras, números e hífen'}), 400
        
        # Verificar se o dslink já existe
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM EVENTO1 WHERE DSLINK = %s", (dslink,))
        if cursor.fetchone()[0] > 0:
            cursor.close()
            return jsonify({'error': 'Este link já está em uso. Escolha outro.'}), 400
        
        # Validação de datas
        try:
            data_inicio = datetime.strptime(data['datainicio'], '%Y-%m-%d').date()
            data_fim = datetime.strptime(data['datafim'], '%Y-%m-%d').date()
            
            if data_fim < data_inicio:
                return jsonify({'error': 'Data de fim deve ser posterior à data de início'}), 400
                
            # Validação de datas de inscrição (se fornecidas)
            if data.get('inicioinscricao') and data.get('fiminscricao'):
                inicio_inscricao = datetime.strptime(data['inicioinscricao'], '%Y-%m-%d').date()
                fim_inscricao = datetime.strptime(data['fiminscricao'], '%Y-%m-%d').date()
                
                if fim_inscricao < inicio_inscricao:
                    return jsonify({'error': 'Data fim de inscrição deve ser posterior ao início'}), 400
                    
        except ValueError:
            return jsonify({'error': 'Formato de data inválido'}), 400
        
        # Processar banner se fornecido
        banner_blob = None
        if data.get('banner'):
            try:
                # Remove o prefixo "data:image/...;base64," se presente
                banner_data = data['banner']
                if 'base64,' in banner_data:
                    banner_data = banner_data.split('base64,')[1]
                banner_blob = base64.b64decode(banner_data)
            except Exception as e:
                return jsonify({'error': 'Erro ao processar imagem do banner'}), 400
        
        # Inserir evento no banco
        query = """
            INSERT INTO EVENTO1 
            (TITULO, SUBTITULO, DATAINICIO, DATAFIM, HRINICIO, DSLINK, 
             DESCRICAO, REGULAMENTO, INICIOINSCRICAO, FIMINSCRICAO, 
             ENDERECO, CIDADEUF, IDORGANIZADOR, OBS, ATIVO, BANNER)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        valores = (
            data.get('titulo', '').strip(),
            data.get('subtitulo', '').strip() if data.get('subtitulo') else None,
            data['datainicio'],
            data['datafim'],
            data.get('hrinicio') if data.get('hrinicio') else None,
            dslink,
            data.get('descricao', ''),
            data.get('regulamento', ''),
            data.get('inicioinscricao') if data.get('inicioinscricao') else None,
            data.get('fiminscricao') if data.get('fiminscricao') else None,
            data.get('endereco', '').strip() if data.get('endereco') else None,
            data.get('cidadeuf', '').strip() if data.get('cidadeuf') else None,
            int(data['idorganizador']),
            data.get('obs', '').strip() if data.get('obs') else None,
            data.get('ativo', 'S'),
            banner_blob
        )
        
        cursor.execute(query, valores)
        mysql.connection.commit()
        evento_id = cursor.lastrowid
        cursor.close()
        
        return jsonify({
            'success': True,
            'message': 'Evento cadastrado com sucesso!',
            'evento_id': evento_id,
            'link_evento': f'/evento/{dslink}'
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'Erro interno do servidor: {str(e)}'}), 500

@app.route('/api/eventos/<int:evento_id>', methods=['PUT'])
def atualizar_evento(evento_id):
    """API para atualizar um evento existente"""
    try:
        data = request.get_json()
        
        # Verificar se o evento existe
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT IDORGANIZADOR, DSLINK 
            FROM EVENTO1 
            WHERE IDEVENTO = %s
        """, (evento_id,))
        
        evento_atual = cursor.fetchone()
        if not evento_atual:
            cursor.close()
            return jsonify({'error': 'Evento não encontrado'}), 404
        
        # Validação e limpeza do dslink se fornecido
        dslink_atual = evento_atual[1]
        if 'dslink' in data:
            dslink = data['dslink'].lower()
            dslink = re.sub(r'[^a-z0-9-]', '', dslink)
            
            if not dslink:
                cursor.close()
                return jsonify({'error': 'Link do evento deve conter apenas letras, números e hífen'}), 400
            
            # Verificar se o novo dslink já existe (exceto no evento atual)
            if dslink != dslink_atual:
                cursor.execute("SELECT COUNT(*) FROM EVENTO1 WHERE DSLINK = %s AND IDEVENTO != %s", (dslink, evento_id))
                if cursor.fetchone()[0] > 0:
                    cursor.close()
                    return jsonify({'error': 'Este link já está em uso. Escolha outro.'}), 400
            
            data['dslink'] = dslink
        
        # Validação de datas
        if 'datainicio' in data and 'datafim' in data:
            try:
                data_inicio = datetime.strptime(data['datainicio'], '%Y-%m-%d').date()
                data_fim = datetime.strptime(data['datafim'], '%Y-%m-%d').date()
                
                if data_fim < data_inicio:
                    cursor.close()
                    return jsonify({'error': 'Data de fim deve ser posterior à data de início'}), 400
                    
            except ValueError:
                cursor.close()
                return jsonify({'error': 'Formato de data inválido'}), 400
        
        # Processar banner se fornecido
        if 'banner' in data and data['banner']:
            try:
                banner_data = data['banner']
                if 'base64,' in banner_data:
                    banner_data = banner_data.split('base64,')[1]
                data['banner'] = base64.b64decode(banner_data)
            except Exception as e:
                cursor.close()
                return jsonify({'error': 'Erro ao processar imagem do banner'}), 400
        
        # Construir query de update dinamicamente
        campos_update = []
        valores = []
        
        campos_permitidos = [
            'titulo', 'subtitulo', 'datainicio', 'datafim', 'hrinicio',
            'dslink', 'descricao', 'regulamento', 'inicioinscricao',
            'fiminscricao', 'endereco', 'cidadeuf', 'obs', 'ativo', 'banner'
        ]
        
        for campo in campos_permitidos:
            if campo in data:
                campos_update.append(f"{campo.upper()} = %s")
                valores.append(data[campo])
        
        if not campos_update:
            cursor.close()
            return jsonify({'error': 'Nenhum campo válido fornecido para atualização'}), 400
        
        valores.append(evento_id)
        query = f"UPDATE EVENTO1 SET {', '.join(campos_update)} WHERE IDEVENTO = %s"
        
        cursor.execute(query, valores)
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({
            'success': True,
            'message': 'Evento atualizado com sucesso!'
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro interno do servidor: {str(e)}'}), 500


@app.route('/api/eventos/<int:evento_id>', methods=['DELETE'])
def deletar_evento(evento_id):
    """API para deletar (desativar) um evento"""
    try:
        cursor = mysql.connection.cursor()
        
        # Verificar se o evento existe
        cursor.execute("SELECT COUNT(*) FROM EVENTO1 WHERE IDEVENTO = %s", (evento_id,))
        if cursor.fetchone()[0] == 0:
            cursor.close()
            return jsonify({'error': 'Evento não encontrado'}), 404
        
        # Em vez de deletar fisicamente, apenas desativar
        cursor.execute("UPDATE EVENTO1 SET ATIVO = 'N' WHERE IDEVENTO = %s", (evento_id,))
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({
            'success': True,
            'message': 'Evento desativado com sucesso!'
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro interno do servidor: {str(e)}'}), 500


@app.route('/api/eventos/verificar-link', methods=['POST'])
def verificar_link():
    """API para verificar se um dslink está disponível"""
    try:
        data = request.get_json()
        dslink = data.get('dslink', '').lower()
        dslink = re.sub(r'[^a-z0-9-]', '', dslink)
        
        if not dslink:
            return jsonify({
                'disponivel': False,
                'message': 'Link deve conter apenas letras, números e hífen'
            })
        
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM EVENTO1 WHERE DSLINK = %s", (dslink,))
        count = cursor.fetchone()[0]
        cursor.close()
        
        disponivel = count == 0
        message = 'Link disponível!' if disponivel else 'Este link já está em uso'
        
        return jsonify({
            'disponivel': disponivel,
            'message': message,
            'dslink': dslink
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/eventos/<int:evento_id>', methods=['GET'])
def obter_evento(evento_id):
    """API para obter dados de um evento específico"""
    try:
        cursor = mysql.connection.cursor()
        query = """
            SELECT IDEVENTO, TITULO, SUBTITULO, DATAINICIO, DATAFIM, 
                   HRINICIO, DSLINK, DESCRICAO, REGULAMENTO, 
                   INICIOINSCRICAO, FIMINSCRICAO, ENDERECO, CIDADEUF, 
                   IDORGANIZADOR, OBS, ATIVO, BANNER
            FROM EVENTO1 
            WHERE IDEVENTO = %s
        """
        cursor.execute(query, (evento_id,))
        evento = cursor.fetchone()
        cursor.close()
        
        if not evento:
            return jsonify({'error': 'Evento não encontrado'}), 404
        
        # Converter para dicionário
        campos = ['idevento', 'titulo', 'subtitulo', 'datainicio', 'datafim',
                 'hrinicio', 'dslink', 'descricao', 'regulamento',
                 'inicioinscricao', 'fiminscricao', 'endereco', 'cidadeuf',
                 'idorganizador', 'obs', 'ativo', 'banner']
        
        evento_dict = {}
        for i, campo in enumerate(campos):
            valor = evento[i]
            # Converter datas para string
            if campo in ['datainicio', 'datafim', 'inicioinscricao', 'fiminscricao'] and valor:
                evento_dict[campo] = valor.strftime('%Y-%m-%d')
            elif campo == 'banner' and valor:
                # Converter BLOB para base64
                evento_dict[campo] = base64.b64encode(valor).decode('utf-8')
                print(f"Banner encontrado para evento {evento_id}, tamanho: {len(valor)} bytes")  # Debug
            else:
                evento_dict[campo] = valor
        
        print(f"Retornando evento {evento_id}, banner presente: {evento_dict.get('banner') is not None}")  # Debug
        
        return jsonify(evento_dict)
        
    except Exception as e:
        print(f"Erro ao obter evento {evento_id}: {str(e)}")  # Debug
        return jsonify({'error': str(e)}), 500

@app.route('/api/eventos', methods=['GET'])
def listar_eventos():
    """API para listar eventos de um organizador"""
    try:
        idorganizador = request.args.get('idorganizador')
        ativo = request.args.get('ativo', 'S')  # Padrão é listar apenas eventos ativos
        
        if not idorganizador:
            return jsonify({'error': 'ID do organizador é obrigatório'}), 400
        
        cursor = mysql.connection.cursor()
        
        # Query base
        query = """
            SELECT IDEVENTO, TITULO, SUBTITULO, DATAINICIO, DATAFIM, 
                   HRINICIO, DSLINK, ENDERECO, CIDADEUF, ATIVO
            FROM EVENTO1 
            WHERE IDORGANIZADOR = %s
        """
        params = [idorganizador]
        
        # Incluir eventos ativos e inativos para o painel administrativo
        query += " ORDER BY DATAINICIO DESC"
        
        cursor.execute(query, params)
        eventos = cursor.fetchall()
        cursor.close()
        
        # Converter para lista de dicionários
        eventos_list = []
        for evento in eventos:
            evento_dict = {
                'idevento': evento[0],
                'titulo': evento[1],
                'subtitulo': evento[2],
                'datainicio': evento[3].strftime('%d/%m/%Y') if evento[3] else None,
                'datafim': evento[4].strftime('%d/%m/%Y') if evento[4] else None,
                'hrinicio': str(evento[5]) if evento[5] else None,
                'dslink': evento[6],
                'endereco': evento[7],
                'cidadeuf': evento[8],
                'ativo': evento[9]
            }
            eventos_list.append(evento_dict)
        
        return jsonify(eventos_list)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

@app.route('/evento/<dslink>')
def visualizar_evento(dslink):
    """Página pública para visualizar um evento"""
    cur = None
    try:
        cur = mysql.connection.cursor()

        # Query para buscar evento
        cur.execute("""
            SELECT IDEVENTO, TITULO, SUBTITULO, DATAINICIO, DATAFIM, 
                   HRINICIO, DESCRICAO, REGULAMENTO, ENDERECO, CIDADEUF,
                   INICIOINSCRICAO, FIMINSCRICAO, ATIVO, BANNER
            FROM EVENTO1 
            WHERE DSLINK = %s AND ATIVO = 'S'
        """, (dslink,))
	    
        evento_data = cur.fetchone()
        
        if not evento_data:
            cur.close()
            return "Evento não encontrado", 404
        
        # Função para formatar data com verificação de tipo
        def formatar_data(data_valor):
            if not data_valor:
                return None
            if isinstance(data_valor, str):
                return data_valor
            if hasattr(data_valor, 'strftime'):
                return data_valor.strftime('%d/%m/%Y')
            return str(data_valor)
        
        def formatar_hora(hora_valor):
            if not hora_valor:
                return None
            if isinstance(hora_valor, str):
                return hora_valor
            if hasattr(hora_valor, 'strftime'):
                return hora_valor.strftime('%H:%M')
            return str(hora_valor)
        
        # Preparar dados para o template
        evento = list(evento_data)
        evento_id = evento_data[0]

        # Formatar datas
        try:
            evento[3] = formatar_data(evento[3])  # DATAINICIO
            evento[4] = formatar_data(evento[4])  # DATAFIM  
            evento[5] = formatar_hora(evento[5])  # HRINICIO
            evento[10] = formatar_data(evento[10])  # INICIOINSCRICAO
            evento[11] = formatar_data(evento[11])  # FIMINSCRICAO
        except Exception as e:
            print(f"Erro formatando datas: {e}")
        
        # Criar objeto compatível com o template - CORRIGIDO OS ÍNDICES
        class EventoCompat:
            def __init__(self, data_list):
                self.data_list = data_list
                self.titulo = data_list[1]          # TITULO (índice 1)
                self.descricao = data_list[6] or ""  # DESCRICAO (índice 6)
                self.regulamento = data_list[7] or "" # REGULAMENTO (índice 7)
                self.local = data_list[8] or ""      # ENDERECO (índice 8)
                self.cidade_uf = data_list[9] or ""  # CIDADEUF (índice 9)
                self.data = data_list[3]             # DATAINICIO (índice 3)
                self.hora = data_list[5]             # HRINICIO (índice 5)
            
            def __getitem__(self, index):
                return self.data_list[index]
        
        evento = EventoCompat(evento)
        
        # Query corrigida para nova estrutura - JOIN entre EVENTO_ITEM e EVENTO_ITEM_LOTES
        cur.execute("""
			SELECT 
			    eil.IDLOTE,
			    ei.IDITEM, 
			    ei.DESCRICAO, 
			    eil.DTINICIO, 
			    eil.DTFIM,
			    eil.NUATLETAS, 
			    eil.LOTE, 
			    eil.DELOTE, 
			    eil.IDITEM_PROXIMO_LOTE, 
			    eil.VLINSCRICAO, 
			    ROUND((eil.VLINSCRICAO * eil.PCTAXA / 100), 2) AS VLTAXA,
			    ROUND(eil.VLINSCRICAO + (eil.VLINSCRICAO * eil.PCTAXA / 100), 2) AS VLTOTAL,
			    (SELECT ROUND((ultimo.VLINSCRICAO / 2), 2) 
			    FROM EVENTO_ITEM_LOTES ultimo 
			    WHERE ultimo.IDLOTE = eil.IDITEM_ULTIMO_LOTE) AS VL_MEIA,
			    (SELECT ROUND(((ultimo.VLINSCRICAO / 2) * ultimo.PCTAXA / 100), 2) 
			    FROM EVENTO_ITEM_LOTES ultimo 
			    WHERE ultimo.IDLOTE = eil.IDITEM_ULTIMO_LOTE) AS VL_TAXA_MEIA,
			    (SELECT ROUND((ultimo.VLINSCRICAO / 2) + ((ultimo.VLINSCRICAO / 2) * ultimo.PCTAXA / 100), 2) 
			    FROM EVENTO_ITEM_LOTES ultimo 
			    WHERE ultimo.IDLOTE = eil.IDITEM_ULTIMO_LOTE) AS VL_TOTAL_MEIA,
			    (SELECT COUNT(IDINSCRICAO) 
			    FROM EVENTO_INSCRICAO 
			    WHERE IDEVENTO = ei.IDEVENTO) AS QTD_INSCRICOES,
			    CASE 
			        WHEN CURDATE() < eil.DTINICIO THEN
			            CASE 
			                WHEN EXISTS (
			                    SELECT 1 
			                    FROM EVENTO_ITEM_LOTES lote_ant
			                    WHERE lote_ant.IDLOTE = (
			                        SELECT IDLOTE FROM EVENTO_ITEM_LOTES WHERE IDITEM_PROXIMO_LOTE = eil.IDLOTE LIMIT 1
			                    )
			                    AND (
			                        SELECT COUNT(IDINSCRICAO) FROM EVENTO_INSCRICAO WHERE IDEVENTO = ei.IDEVENTO
			                    ) >= lote_ant.NUATLETAS
			                ) THEN 'ABERTO'
			                ELSE 'NÃO INICIADO'
			            END
			        WHEN CURDATE() BETWEEN eil.DTINICIO AND eil.DTFIM THEN
			            CASE 
			                WHEN (SELECT COUNT(IDINSCRICAO) FROM EVENTO_INSCRICAO WHERE IDEVENTO = ei.IDEVENTO) < eil.NUATLETAS THEN 'ABERTO'
			                ELSE 'ESGOTADO'
			            END
			        WHEN CURDATE() > eil.DTFIM THEN 'ENCERRADO'
			        ELSE 'ENCERRADO'
			    END AS STATUS_LOTE
			FROM EVENTO_ITEM_LOTES eil
			JOIN EVENTO_ITEM ei ON eil.IDITEM = ei.IDITEM
			WHERE ei.IDEVENTO = %s
			ORDER BY 
			    CASE 
			        WHEN (
			            CASE 
			                WHEN CURDATE() < eil.DTINICIO THEN
			                    CASE 
			                        WHEN EXISTS (
			                            SELECT 1 
			                            FROM EVENTO_ITEM_LOTES lote_ant
			                            WHERE lote_ant.IDLOTE = (
			                                SELECT IDLOTE FROM EVENTO_ITEM_LOTES WHERE IDITEM_PROXIMO_LOTE = eil.IDLOTE LIMIT 1
			                            )
			                            AND (
			                                SELECT COUNT(IDINSCRICAO) FROM EVENTO_INSCRICAO WHERE IDEVENTO = ei.IDEVENTO
			                            ) >= lote_ant.NUATLETAS
			                        ) THEN 'ABERTO'
			                        ELSE 'NÃO INICIADO'
			                    END
			                WHEN CURDATE() BETWEEN eil.DTINICIO AND eil.DTFIM THEN
			                    CASE 
			                        WHEN (SELECT COUNT(IDINSCRICAO) FROM EVENTO_INSCRICAO WHERE IDEVENTO = ei.IDEVENTO) < eil.NUATLETAS THEN 'ABERTO'
			                        ELSE 'ESGOTADO'
			                    END
			                WHEN CURDATE() > eil.DTFIM THEN 'ENCERRADO'
			                ELSE 'ENCERRADO'
			            END
			        ) = 'ABERTO' THEN 1
			        WHEN (
			            CASE 
			                WHEN CURDATE() < eil.DTINICIO THEN
			                    CASE 
			                        WHEN EXISTS (
			                            SELECT 1 
			                            FROM EVENTO_ITEM_LOTES lote_ant
			                            WHERE lote_ant.IDLOTE = (
			                                SELECT IDLOTE FROM EVENTO_ITEM_LOTES WHERE IDITEM_PROXIMO_LOTE = eil.IDLOTE LIMIT 1
			                            )
			                            AND (
			                                SELECT COUNT(IDINSCRICAO) FROM EVENTO_INSCRICAO WHERE IDEVENTO = ei.IDEVENTO
			                            ) >= lote_ant.NUATLETAS
			                        ) THEN 'ABERTO'
			                        ELSE 'NÃO INICIADO'
			                    END
			                WHEN CURDATE() BETWEEN eil.DTINICIO AND eil.DTFIM THEN
			                    CASE 
			                        WHEN (SELECT COUNT(IDINSCRICAO) FROM EVENTO_INSCRICAO WHERE IDEVENTO = ei.IDEVENTO) < eil.NUATLETAS THEN 'ABERTO'
			                        ELSE 'ESGOTADO'
			                    END
			                WHEN CURDATE() > eil.DTFIM THEN 'ENCERRADO'
			                ELSE 'ENCERRADO'
			            END
			        ) = 'NÃO INICIADO' THEN 2
			        WHEN (
			            CASE 
			                WHEN CURDATE() < eil.DTINICIO THEN
			                    CASE 
			                        WHEN EXISTS (
			                            SELECT 1 
			                            FROM EVENTO_ITEM_LOTES lote_ant
			                            WHERE lote_ant.IDLOTE = (
			                                SELECT IDLOTE FROM EVENTO_ITEM_LOTES WHERE IDITEM_PROXIMO_LOTE = eil.IDLOTE LIMIT 1
			                            )
			                            AND (
			                                SELECT COUNT(IDINSCRICAO) FROM EVENTO_INSCRICAO WHERE IDEVENTO = ei.IDEVENTO
			                            ) >= lote_ant.NUATLETAS
			                        ) THEN 'ABERTO'
			                        ELSE 'NÃO INICIADO'
			                    END
			                WHEN CURDATE() BETWEEN eil.DTINICIO AND eil.DTFIM THEN
			                    CASE 
			                        WHEN (SELECT COUNT(IDINSCRICAO) FROM EVENTO_INSCRICAO WHERE IDEVENTO = ei.IDEVENTO) < eil.NUATLETAS THEN 'ABERTO'
			                        ELSE 'ESGOTADO'
			                    END
			                WHEN CURDATE() > eil.DTFIM THEN 'ENCERRADO'
			                ELSE 'ENCERRADO'
			            END
			        ) = 'ESGOTADO' THEN 3
			        ELSE 4 -- ENCERRADO
			    END,
			    eil.LOTE, 
			    ei.KM;
        """, (evento_id,))
        
        lotes_data = cur.fetchall()

        # Função para formatar valores
        def formatar_valor_brasileiro(valor):
            if valor is None:
                return "0,00"
            return f"{float(valor):.2f}".replace('.', ',')

        # Processar lotes
        lotes = []
        for lote in lotes_data:
            # Formatar data DTFIM
            dtfim_formatada = ""
            if lote[4]:  # DTFIM
                if isinstance(lote[4], str):
                    try:
                        from datetime import datetime
                        dt = datetime.strptime(lote[4], '%Y-%m-%d')
                        dtfim_formatada = dt.strftime('%d/%m/%Y')
                    except:
                        dtfim_formatada = lote[4]
                else:
                    dtfim_formatada = lote[4].strftime('%d/%m/%Y')
            
            lote_info = {
                'idlote': lote[0],  # IDLOTE - chave primária da tabela EVENTO_ITEM_LOTES
                'iditem': lote[1],  # IDITEM - referência para EVENTO_ITEM
                'descricao': lote[2],
                'dtinicio': lote[3],
                'dtfim': lote[4],
                'dtfim_formatada': dtfim_formatada,
                'nuatletas': lote[5],
                'lote': lote[6],
                'delote': lote[7],
                'iditem_proximo_lote': lote[8],
                'vlinscricao': lote[9],
                'vltaxa': lote[10],
                'vltotal': lote[11],
                # Valores formatados
                'vlinscricao_formatada': formatar_valor_brasileiro(lote[9]),
                'vltaxa_formatada': formatar_valor_brasileiro(lote[10]),
                'vltotal_formatada': formatar_valor_brasileiro(lote[11]),
                'vl_meia': lote[12],
                'vl_taxa_meia': lote[13],
                'vl_total_meia': lote[14],
                'vl_meia_formatada': formatar_valor_brasileiro(lote[12]),
                'vl_taxa_meia_formatada': formatar_valor_brasileiro(lote[13]),
                'vl_total_meia_formatada': formatar_valor_brasileiro(lote[14]),
                'qtd_inscricoes': lote[15],
                'status_lote': lote[16]
            }
            lotes.append(lote_info)

        # Query para buscar imagens do evento
        cur.execute("""
            SELECT ID, IDEVENTO, TITULO_IMG, IMG
            FROM EVENTO_IMG
            WHERE IDEVENTO = %s
            ORDER BY ID
        """, (evento_id,))
        
        imagens_data = cur.fetchall()
        
        # Processar imagens
        imagens_evento = []
        for imagem in imagens_data:
            try:
                if imagem[3] and len(imagem[3]) > 0:  # IMG não é vazio
                    import base64
                    img_base64 = base64.b64encode(imagem[3]).decode('utf-8')
                    
                    imagem_info = {
                        'id': imagem[0],
                        'idevento': imagem[1],
                        'titulo_img': imagem[2] or 'Imagem do Evento',
                        'img_base64': img_base64
                    }
                    imagens_evento.append(imagem_info)
            except Exception as e:
                print(f"Erro processando imagem ID {imagem[0]}: {e}")
                continue

        # Processar banner - CORRIGIDO O ÍNDICE DO BANNER
        banner_base64 = None
        try:
            if evento_data[13] and len(evento_data[13]) > 0:  # BANNER é o índice 13
                import base64
                banner_base64 = base64.b64encode(evento_data[13]).decode('utf-8')
        except Exception as e:
            print(f"Erro processando banner: {e}")
            banner_base64 = None
        
        return render_template('evento_publico.html', 
                             evento=evento, 
                             lotes=lotes, 
                             banner=banner_base64,
                             imagens_evento=imagens_evento) 
    
    except Exception as e:
        print(f"Erro na função visualizar_evento: {e}")
        if cur:
            cur.close()
        return "Erro interno do servidor", 500
    
    finally:
        if cur:
            cur.close()


@app.route('/api/eventos/<int:evento_id>/lotes', methods=['GET'])
def get_lotes(evento_id):
    """Buscar lotes de um evento"""
    try:
        cursor = mysql.connection.cursor()
        
        # Primeiro, vamos testar se o evento existe
        cursor.execute("SELECT COUNT(*) FROM EVENTO1 WHERE IDEVENTO = %s", (evento_id,))
        if cursor.fetchone()[0] == 0:
            cursor.close()
            return jsonify({'error': 'Evento não encontrado'}), 404
        
        # Query com JOIN para buscar dados das duas tabelas
        query = """
            SELECT 
                ei.IDITEM, ei.IDEVENTO, ei.DESCRICAO, ei.KM,
                eil.IDLOTE, eil.VLINSCRICAO, eil.PCTAXA,
                eil.DTINICIO, eil.DTFIM, eil.NUATLETAS, eil.LOTE, eil.DELOTE,  # ← AGORA eil.NUATLETAS
                eil.IDITEM_ULTIMO_LOTE, eil.IDITEM_PROXIMO_LOTE
            FROM EVENTO_ITEM ei
            LEFT JOIN EVENTO_ITEM_LOTES eil ON ei.IDITEM = eil.IDITEM
            WHERE ei.IDEVENTO = %s
            ORDER BY eil.LOTE, ei.KM
        """
        
        cursor.execute(query, (evento_id,))
        
        columns = [desc[0] for desc in cursor.description]
        lotes = []
        
        for row in cursor.fetchall():
            lote_dict = dict(zip(columns, row))
            
            # Converter Decimal para float para JSON
            if lote_dict.get('KM'):
                lote_dict['KM'] = float(lote_dict['KM'])
            if lote_dict.get('VLINSCRICAO'):
                lote_dict['VLINSCRICAO'] = float(lote_dict['VLINSCRICAO'])
            if lote_dict.get('PCTAXA'):
                lote_dict['PCTAXA'] = float(lote_dict['PCTAXA'])
            
            # Tratar datas - converter para string no formato YYYY-MM-DD
            if lote_dict.get('DTINICIO'):
                if hasattr(lote_dict['DTINICIO'], 'strftime'):
                    lote_dict['DTINICIO'] = lote_dict['DTINICIO'].strftime('%Y-%m-%d')
                else:
                    lote_dict['DTINICIO'] = str(lote_dict['DTINICIO']) if lote_dict['DTINICIO'] else None
            
            if lote_dict.get('DTFIM'):
                if hasattr(lote_dict['DTFIM'], 'strftime'):
                    lote_dict['DTFIM'] = lote_dict['DTFIM'].strftime('%Y-%m-%d')
                else:
                    lote_dict['DTFIM'] = str(lote_dict['DTFIM']) if lote_dict['DTFIM'] else None
            
            lotes.append(lote_dict)
        
        cursor.close()
        return jsonify(lotes), 200
        
    except Exception as e:
        print(f"Erro ao buscar lotes: {str(e)}")
        import traceback
        traceback.print_exc()
        
        if 'cursor' in locals():
            cursor.close()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500


##### ALTERADO POR MIM.... TESTAR E VERIFICAR
@app.route('/api/eventos/<int:evento_id>/lotes', methods=['POST'])
def create_lotes(evento_id):
    """Criar lotes para um evento"""
    try:
        data = request.json
        lotes_data = data.get('lotes', [])
        
        if not lotes_data:
            return jsonify({'error': 'Nenhum lote fornecido'}), 400
        
        cursor = mysql.connection.cursor()
        
        # Organizar lotes por descrição para inserir items únicos primeiro
        lotes_por_descricao = {}
        for lote in lotes_data:
            descricao = lote['descricao']
            km = lote['km']
            nuatletas = lote['nuatletas']
            chave = f"{descricao}_{km}"
            
            if chave not in lotes_por_descricao:
                lotes_por_descricao[chave] = {
                    'item_info': {
                        'descricao': descricao,
                        'km': km,
                        'nuatletas': nuatletas
                    },
                    'lotes': []
                }
            lotes_por_descricao[chave]['lotes'].append(lote)
        
        # Ordenar lotes dentro de cada descrição
        for chave in lotes_por_descricao:
            lotes_por_descricao[chave]['lotes'].sort(key=lambda x: x['lote'])
        
        # Primeiro, inserir os items únicos na tabela EVENTO_ITEM
        items_criados = {}
        
        for chave, dados in lotes_por_descricao.items():
            item_info = dados['item_info']
            
            # Inserir item na tabela EVENTO_ITEM
            query_item = """
                INSERT INTO EVENTO_ITEM (IDEVENTO, DESCRICAO, KM)
                VALUES (%s, %s, %s)
            """

            cursor.execute(query_item, (
                evento_id,
                item_info['descricao'],
                item_info['km']
            ))

            # Obter o ID do item inserido
            iditem = cursor.lastrowid
            items_criados[chave] = iditem
        
        # Agora inserir os lotes na tabela EVENTO_ITEM_LOTES
        for chave, dados in lotes_por_descricao.items():
            iditem = items_criados[chave]
            lotes_desc = dados['lotes']
            
            # Calcular relacionamentos entre lotes
            for i, lote in enumerate(lotes_desc):
                # Para IDITEM_ULTIMO_LOTE, vamos calcular depois que todos os lotes forem inseridos
                # Para IDITEM_PROXIMO_LOTE, será o próximo lote ou 0 se for o último
                
                # Calcular PCTAXA baseado no valor
                valor = float(lote['vlinscricao'])
                if valor <= 100:
                    pctaxa = 10
                elif valor <= 150:
                    pctaxa = 9
                elif valor <= 200:
                    pctaxa = 8
                else:
                    pctaxa = 7
                
                # Tratar datas vazias
                dtinicio = lote['dtinicio'] if lote['dtinicio'] and lote['dtinicio'].strip() else None
                dtfim = lote['dtfim'] if lote['dtfim'] and lote['dtfim'].strip() else None
                
                query_lote = """
                    INSERT INTO EVENTO_ITEM_LOTES 
                    (IDITEM, IDEVENTO, VLINSCRICAO, PCTAXA, 
                     DTINICIO, DTFIM, NUATLETAS, LOTE, DELOTE, 
                     IDITEM_ULTIMO_LOTE, IDITEM_PROXIMO_LOTE)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                
                cursor.execute(query_lote, (
                    iditem,
                    evento_id,
                    lote['vlinscricao'],
                    pctaxa,
                    dtinicio,
                    dtfim,
                    lote['nuatletas'] if lote['nuatletas'] else None,
                    lote['lote'],
                    lote['delote'],
                    0,  # Será atualizado abaixo
                    0   # Será atualizado abaixo
                ))
        
        # Agora atualizar os relacionamentos IDITEM_ULTIMO_LOTE e IDITEM_PROXIMO_LOTE
        for chave, dados in lotes_por_descricao.items():
            iditem = items_criados[chave]
            
            # Buscar todos os lotes inseridos para este item, ordenados por LOTE
            cursor.execute("""
                SELECT IDLOTE, LOTE FROM EVENTO_ITEM_LOTES 
                WHERE IDITEM = %s 
                ORDER BY LOTE
            """, (iditem,))
            
            lotes_inseridos = cursor.fetchall()
            
            if lotes_inseridos:
                ultimo_lote_id = lotes_inseridos[-1][0]  # IDLOTE do último lote
                
                for i, (idlote_atual, lote_num) in enumerate(lotes_inseridos):
                    proximo_lote_id = lotes_inseridos[i + 1][0] if i < len(lotes_inseridos) - 1 else 0
                    
                    cursor.execute("""
                        UPDATE EVENTO_ITEM_LOTES 
                        SET IDITEM_ULTIMO_LOTE = %s, IDITEM_PROXIMO_LOTE = %s 
                        WHERE IDLOTE = %s
                    """, (ultimo_lote_id, proximo_lote_id, idlote_atual))
        
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({'message': 'Lotes criados com sucesso'}), 201
        
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/eventos/<int:evento_id>/items', methods=['POST'])
def create_item_for_evento(evento_id):
    """Criar um novo item para um evento específico"""
    try:
        data = request.json
        
        # Validações
        if not data.get('descricao') or not data.get('km'):
            return jsonify({'error': 'Campos obrigatórios: descricao, km'}), 400
        
        cursor = mysql.connection.cursor()
        
        # Verificar se o evento existe
        cursor.execute("SELECT IDEVENTO FROM EVENTO1 WHERE IDEVENTO = %s", (evento_id,))
        if not cursor.fetchone():
            cursor.close()
            return jsonify({'error': 'Evento não encontrado'}), 404
        
        # Inserir o novo item
        query = """
            INSERT INTO EVENTO_ITEM (IDEVENTO, DESCRICAO, KM)
            VALUES (%s, %s, %s)
        """
        
        cursor.execute(query, (
            evento_id,
            data['descricao'],
            float(data['km'])
        ))
        
        mysql.connection.commit()
        item_id = cursor.lastrowid
        cursor.close()
        
        return jsonify({'message': 'Item criado com sucesso', 'iditem': item_id}), 201
        
    except Exception as e:
        mysql.connection.rollback()
        if 'cursor' in locals():
            cursor.close()
        return jsonify({'error': str(e)}), 500


@app.route('/api/lotes/<int:idlote>', methods=['DELETE'])
def delete_lote(idlote):
    """Excluir um lote específico"""
    try:
        cursor = mysql.connection.cursor()
        
        # Buscar dados do lote antes de excluir
        cursor.execute("""
            SELECT eil.IDEVENTO, eil.IDITEM, ei.KM, eil.LOTE 
            FROM EVENTO_ITEM_LOTES eil
            JOIN EVENTO_ITEM ei ON eil.IDITEM = ei.IDITEM
            WHERE eil.IDLOTE = %s
        """, (idlote,))
        
        lote_info = cursor.fetchone()
        
        if not lote_info:
            return jsonify({'error': 'Lote não encontrado'}), 404
        
        evento_id, iditem, km, lote_num = lote_info
        
        # Excluir o lote
        cursor.execute("DELETE FROM EVENTO_ITEM_LOTES WHERE IDLOTE = %s", (idlote,))
        
        # Verificar se ainda existem lotes para este item
        cursor.execute("""
            SELECT COUNT(*) FROM EVENTO_ITEM_LOTES WHERE IDITEM = %s
        """, (iditem,))
        
        total_lotes = cursor.fetchone()[0]
        
        if total_lotes == 0:
            # Se não há mais lotes, excluir o item também
            cursor.execute("DELETE FROM EVENTO_ITEM WHERE IDITEM = %s", (iditem,))
        else:
            # Reajustar os relacionamentos dos lotes restantes
            cursor.execute("""
                SELECT IDLOTE, LOTE FROM EVENTO_ITEM_LOTES 
                WHERE IDITEM = %s 
                ORDER BY LOTE
            """, (iditem,))
            
            lotes_restantes = cursor.fetchall()
            
            if lotes_restantes:
                ultimo_lote_id = lotes_restantes[-1][0]  # IDLOTE do último lote
                
                for i, (lote_id, lote_ordem) in enumerate(lotes_restantes):
                    proximo_lote_id = lotes_restantes[i + 1][0] if i < len(lotes_restantes) - 1 else 0
                    
                    cursor.execute("""
                        UPDATE EVENTO_ITEM_LOTES 
                        SET IDITEM_ULTIMO_LOTE = %s, IDITEM_PROXIMO_LOTE = %s 
                        WHERE IDLOTE = %s
                    """, (ultimo_lote_id, proximo_lote_id, lote_id))
        
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({'message': 'Lote excluído com sucesso'}), 200
        
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/lotes/<int:idlote>', methods=['PUT'])
def update_lote(idlote):
    """Atualizar um lote específico"""
    try:
        data = request.json
        cursor = mysql.connection.cursor()
        
        # Buscar o IDITEM do lote
        cursor.execute("SELECT IDITEM FROM EVENTO_ITEM_LOTES WHERE IDLOTE = %s", (idlote,))
        result = cursor.fetchone()
        
        if not result:
            return jsonify({'error': 'Lote não encontrado'}), 404
        
        iditem = result[0]
        
        # Atualizar dados do item se fornecidos
        if 'descricao' in data or 'km' in data:
            update_item_query = "UPDATE EVENTO_ITEM SET "
            item_params = []
            
            if 'descricao' in data:
                update_item_query += "DESCRICAO = %s, "
                item_params.append(data['descricao'])
            
            if 'km' in data:
                update_item_query += "KM = %s, "
                item_params.append(data['km'])
            
            update_item_query = update_item_query.rstrip(', ') + " WHERE IDITEM = %s"
            item_params.append(iditem)
            
            cursor.execute(update_item_query, item_params)
        
        # Calcular PCTAXA baseado no novo valor
        valor = float(data.get('vlinscricao', 0))
        if valor <= 100:
            pctaxa = 10
        elif valor <= 150:
            pctaxa = 9
        elif valor <= 200:
            pctaxa = 8
        else:
            pctaxa = 7
        
        # Atualizar dados do lote
        query = """
            UPDATE EVENTO_ITEM_LOTES 
            SET VLINSCRICAO = %s, PCTAXA = %s,
                DTINICIO = %s, DTFIM = %s, NUATLETAS = %s, 
                LOTE = %s, DELOTE = %s
            WHERE IDLOTE = %s
        """
        
        cursor.execute(query, (
            data.get('vlinscricao'),
            pctaxa,
            data.get('dtinicio') if data.get('dtinicio') else None,
            data.get('dtfim') if data.get('dtfim') else None,
            data.get('nuatletas') if data.get('nuatletas') else None,
            data.get('lote'),
            data.get('delote'),
            idlote
        ))
        
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({'message': 'Lote atualizado com sucesso'}), 200
        
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/lote-inscricao2/<int:idlote>')
def get_lote_inscricao2(idlote):
    """API para obter dados de um lote específico para inscrição"""
    
    print(" ::::: DEBUG  def get_lote_inscricao2 ::::::")
    try:
        cur = mysql.connection.cursor()
        
        cur.execute("""
            SELECT 
              eil.IDLOTE,
              ei.IDITEM, 
              ei.DESCRICAO, 
              eil.VLINSCRICAO, 
              ROUND((eil.VLINSCRICAO * eil.PCTAXA / 100), 2) AS VLTAXA,
              ROUND(eil.VLINSCRICAO + (eil.VLINSCRICAO * eil.PCTAXA / 100), 2) AS VLTOTAL,
              (SELECT ROUND((VLINSCRICAO / 2), 2) 
               FROM EVENTO_ITEM_LOTES 
               WHERE IDLOTE = eil.IDITEM_ULTIMO_LOTE) AS VL_MEIA,
              (SELECT ROUND(((VLINSCRICAO / 2) * PCTAXA / 100), 2) 
               FROM EVENTO_ITEM_LOTES 
               WHERE IDLOTE = eil.IDITEM_ULTIMO_LOTE) AS VL_TAXA_MEIA,
              (SELECT ROUND((VLINSCRICAO / 2) + ((VLINSCRICAO / 2) * PCTAXA / 100), 2) 
               FROM EVENTO_ITEM_LOTES 
               WHERE IDLOTE = eil.IDITEM_ULTIMO_LOTE) AS VL_TOTAL_MEIA,
              e.TITULO, e.IDEVENTO
            FROM EVENTO_ITEM_LOTES eil
            JOIN EVENTO_ITEM ei ON eil.IDITEM = ei.IDITEM
            JOIN EVENTO1 e ON ei.IDEVENTO = e.IDEVENTO
            WHERE eil.IDLOTE = %s
        """, (idlote,))
        
        lote_data = cur.fetchone()
        cur.close()
        
        if not lote_data:
            return jsonify({'error': 'Lote não encontrado'}), 404
        
        # Função para formatar valores em formato brasileiro
        def formatar_valor_brasileiro_api(valor):
            """Converte valor decimal para formato brasileiro (vírgula como separador decimal)"""
            if valor is None:
                return "0,00"
            return f"{float(valor):.2f}".replace('.', ',')
        
        return jsonify({
            'idevento': lote_data[10],
            'idlote': lote_data[0],    # Novo campo IDLOTE
            'iditem': lote_data[1],    # IDITEM da tabela EVENTO_ITEM
            'titulo': lote_data[9],
            'descricao': lote_data[2],
            'vlinscricao': float(lote_data[3]) if lote_data[3] else 0,
            'vltaxa': float(lote_data[4]) if lote_data[4] else 0,
            'vltotal': float(lote_data[5]) if lote_data[5] else 0,
            'vlinscricao_meia': float(lote_data[6]) if lote_data[6] else 0,
            'vltaxa_meia': float(lote_data[7]) if lote_data[7] else 0,
            'vltotal_meia': float(lote_data[8]) if lote_data[8] else 0,
            # Valores formatados em padrão brasileiro para exibição
            'vlinscricao_formatada': formatar_valor_brasileiro_api(lote_data[3]),
            'vltaxa_formatada': formatar_valor_brasileiro_api(lote_data[4]),
            'vltotal_formatada': formatar_valor_brasileiro_api(lote_data[5]),
            'vlinscricao_meia_formatada': formatar_valor_brasileiro_api(lote_data[6]),
            'vltaxa_meia_formatada': formatar_valor_brasileiro_api(lote_data[7]),
            'vltotal_meia_formatada': formatar_valor_brasileiro_api(lote_data[8])
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro ao buscar dados do lote: {str(e)}'}), 500


###############################################################
###############################################################
###############################################################
# ROTA ADICIONAL: Buscar apenas items de um evento (sem lotes)
@app.route('/api/eventos/<int:evento_id>/items', methods=['GET'])
def get_items(evento_id):
    """Buscar apenas os items de um evento (sem lotes)"""
    try:
        cursor = mysql.connection.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM EVENTO1 WHERE IDEVENTO = %s", (evento_id,))
        if cursor.fetchone()[0] == 0:
            cursor.close()
            return jsonify({'error': 'Evento não encontrado'}), 404
        
        query = """
            SELECT IDITEM, IDEVENTO, DESCRICAO, KM
            FROM EVENTO_ITEM 
            WHERE IDEVENTO = %s
            ORDER BY KM
        """
        
        cursor.execute(query, (evento_id,))
        
        columns = [desc[0] for desc in cursor.description]
        items = []
        
        for row in cursor.fetchall():
            item_dict = dict(zip(columns, row))
            
            # Converter Decimal para float para JSON
            if item_dict.get('KM'):
                item_dict['KM'] = float(item_dict['KM'])
            
            items.append(item_dict)
        
        cursor.close()
        return jsonify(items), 200
        
    except Exception as e:
        print(f"Erro ao buscar items: {str(e)}")
        import traceback
        traceback.print_exc()
        
        if 'cursor' in locals():
            cursor.close()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500


# Rota para criar um novo item
@app.route('/api/items', methods=['POST'])
def create_item():
    """Criar um novo item para um evento"""
    try:
        data = request.json
        
        # Validações
        if not data.get('idevento') or not data.get('descricao') or not data.get('km'):
            return jsonify({'error': 'Campos obrigatórios: idevento, descricao, km'}), 400
        
        cursor = mysql.connection.cursor()
        
        # Verificar se o evento existe
        cursor.execute("SELECT IDEVENTO FROM EVENTO1 WHERE IDEVENTO = %s", (data['idevento'],))
        if not cursor.fetchone():
            cursor.close()
            return jsonify({'error': 'Evento não encontrado'}), 404
        
        # Inserir o novo item
        query = """
            INSERT INTO EVENTO_ITEM (IDEVENTO, DESCRICAO, KM)
            VALUES (%s, %s, %s)
        """
        
        cursor.execute(query, (
            data['idevento'],
            data['descricao'],
            float(data['km'])
        ))
        
        mysql.connection.commit()
        item_id = cursor.lastrowid
        cursor.close()
        
        return jsonify({'message': 'Item criado com sucesso', 'iditem': item_id}), 201
        
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'error': str(e)}), 500


#############################################################
#############################################################
#############################################################


# ROTA ADICIONAL: Buscar lotes de um item específico
@app.route('/api/items/<int:iditem>/lotes', methods=['GET'])
def get_lotes_by_item(iditem):
    """Buscar lotes de um item específico"""
    try:
        cursor = mysql.connection.cursor()
        
        query = """
            SELECT 
                eil.IDLOTE, eil.IDITEM, eil.IDEVENTO, eil.VLINSCRICAO, eil.PCTAXA,
                eil.DTINICIO, eil.DTFIM, eil.NUATLETAS, eil.LOTE, eil.DELOTE,  # ← AGORA eil.NUATLETAS
                eil.IDITEM_ULTIMO_LOTE, eil.IDITEM_PROXIMO_LOTE,
                ei.DESCRICAO, ei.KM
            FROM EVENTO_ITEM_LOTES eil
            JOIN EVENTO_ITEM ei ON eil.IDITEM = ei.IDITEM
            WHERE eil.IDITEM = %s
            ORDER BY eil.LOTE
        """

        cursor.execute(query, (iditem,))
        
        columns = [desc[0] for desc in cursor.description]
        lotes = []
        
        for row in cursor.fetchall():
            lote_dict = dict(zip(columns, row))
            
            # Converter Decimal para float para JSON
            if lote_dict.get('KM'):
                lote_dict['KM'] = float(lote_dict['KM'])
            if lote_dict.get('VLINSCRICAO'):
                lote_dict['VLINSCRICAO'] = float(lote_dict['VLINSCRICAO'])
            if lote_dict.get('PCTAXA'):
                lote_dict['PCTAXA'] = float(lote_dict['PCTAXA'])
            
            # Tratar datas
            if lote_dict.get('DTINICIO'):
                if hasattr(lote_dict['DTINICIO'], 'strftime'):
                    lote_dict['DTINICIO'] = lote_dict['DTINICIO'].strftime('%Y-%m-%d')
                else:
                    lote_dict['DTINICIO'] = str(lote_dict['DTINICIO']) if lote_dict['DTINICIO'] else None
            
            if lote_dict.get('DTFIM'):
                if hasattr(lote_dict['DTFIM'], 'strftime'):
                    lote_dict['DTFIM'] = lote_dict['DTFIM'].strftime('%Y-%m-%d')
                else:
                    lote_dict['DTFIM'] = str(lote_dict['DTFIM']) if lote_dict['DTFIM'] else None
            
            lotes.append(lote_dict)
        
        cursor.close()
        return jsonify(lotes), 200
        
    except Exception as e:
        print(f"Erro ao buscar lotes do item: {str(e)}")
        import traceback
        traceback.print_exc()
        
        if 'cursor' in locals():
            cursor.close()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500


# Rota para atualizar um item
@app.route('/api/items/<int:iditem>', methods=['PUT'])
def update_item(iditem):
    """Atualizar um item existente"""
    try:
        data = request.json
        
        # Validações
        if not data.get('descricao') or not data.get('km'):
            return jsonify({'error': 'Campos obrigatórios: descricao, km'}), 400
        
        cursor = mysql.connection.cursor()
        
        # Verificar se o item existe
        cursor.execute("SELECT IDITEM FROM EVENTO_ITEM WHERE IDITEM = %s", (iditem,))
        if not cursor.fetchone():
            cursor.close()
            return jsonify({'error': 'Item não encontrado'}), 404
        
        # Atualizar o item
        query = """
            UPDATE EVENTO_ITEM 
            SET DESCRICAO = %s, KM = %s
            WHERE IDITEM = %s
        """

        cursor.execute(query, (
            data['descricao'],
            float(data['km']),
            iditem
        ))
        
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({'message': 'Item atualizado com sucesso'}), 200
        
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'error': str(e)}), 500

# Rota para excluir um item
@app.route('/api/items/<int:iditem>', methods=['DELETE'])
def delete_item(iditem):
    """Excluir um item e todos os seus lotes"""
    try:
        cursor = mysql.connection.cursor()
        
        # Verificar se o item existe
        cursor.execute("SELECT IDITEM FROM EVENTO_ITEM WHERE IDITEM = %s", (iditem,))
        if not cursor.fetchone():
            cursor.close()
            return jsonify({'error': 'Item não encontrado'}), 404
        
        # Excluir primeiro os lotes (devido à foreign key)
        cursor.execute("DELETE FROM EVENTO_ITEM_LOTES WHERE IDITEM = %s", (iditem,))
        
        # Depois excluir o item
        cursor.execute("DELETE FROM EVENTO_ITEM WHERE IDITEM = %s", (iditem,))
        
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({'message': 'Item excluído com sucesso'}), 200
        
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'error': str(e)}), 500

# Rota para criar um lote
@app.route('/api/lotes', methods=['POST'])
def create_lote():
    """Criar um novo lote para um item"""
    try:
        data = request.json
        
        # Validações
        required_fields = ['iditem', 'idevento', 'vlinscricao', 'lote']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Campo obrigatório: {field}'}), 400
        
        cursor = mysql.connection.cursor()
        
        # Verificar se o item existe
        cursor.execute("SELECT IDITEM FROM EVENTO_ITEM WHERE IDITEM = %s", (data['iditem'],))
        if not cursor.fetchone():
            cursor.close()
            return jsonify({'error': 'Item não encontrado'}), 404
        
        # Tratar datas vazias
        dtinicio = data.get('dtinicio') if data.get('dtinicio') and str(data.get('dtinicio')).strip() else None
        dtfim = data.get('dtfim') if data.get('dtfim') and str(data.get('dtfim')).strip() else None
        
        # Inserir o lote
        query = """
            INSERT INTO EVENTO_ITEM_LOTES 
            (IDITEM, IDEVENTO, VLINSCRICAO, PCTAXA, DTINICIO, DTFIM, 
            NUATLETAS, LOTE, DELOTE, IDITEM_ULTIMO_LOTE, IDITEM_PROXIMO_LOTE)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(query, (
            data['iditem'],
            data['idevento'],
            float(data['vlinscricao']),
            float(data['pctaxa']),
            dtinicio,
            dtfim,
            int(data['nuatletas']) if data.get('nuatletas') else None,  # ← ADICIONAR ESTA LINHA
            int(data['lote']),
            data.get('delote', ''),
            0,
            0
        ))

        lote_id = cursor.lastrowid
        
        # Atualizar relacionamentos entre lotes do mesmo item
        update_lote_relationships(cursor, data['iditem'])
        
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({'message': 'Lote criado com sucesso', 'idlote': lote_id}), 201
        
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'error': str(e)}), 500


# Função auxiliar para atualizar relacionamentos entre lotes
def update_lote_relationships(cursor, iditem):
    """Atualizar os relacionamentos IDITEM_ULTIMO_LOTE e IDITEM_PROXIMO_LOTE"""
    try:
        # Buscar todos os lotes do item ordenados por LOTE
        cursor.execute("""
            SELECT IDLOTE FROM EVENTO_ITEM_LOTES 
            WHERE IDITEM = %s 
            ORDER BY LOTE
        """, (iditem,))
        
        lotes = cursor.fetchall()
        
        if lotes:
            ultimo_lote_id = lotes[-1][0]  # IDLOTE do último lote
            
            for i, (idlote_atual,) in enumerate(lotes):
                proximo_lote_id = lotes[i + 1][0] if i < len(lotes) - 1 else 0
                
                cursor.execute("""
                    UPDATE EVENTO_ITEM_LOTES 
                    SET IDITEM_ULTIMO_LOTE = %s, IDITEM_PROXIMO_LOTE = %s 
                    WHERE IDLOTE = %s
                """, (ultimo_lote_id, proximo_lote_id, idlote_atual))
                
    except Exception as e:
        raise e


# Rota para buscar itens de um evento específico
@app.route('/api/eventos/<int:evento_id>/items', methods=['GET'])
def get_items_by_evento(evento_id):
    """Buscar todos os itens de um evento específico"""
    try:
        cursor = mysql.connection.cursor()
        
        query = """
            SELECT IDITEM, IDEVENTO, DESCRICAO, KM
            FROM EVENTO_ITEM 
            WHERE IDEVENTO = %s
            ORDER BY DESCRICAO, KM
        """
        
        cursor.execute(query, (evento_id,))
        
        columns = [desc[0] for desc in cursor.description]
        items = []
        
        for row in cursor.fetchall():
            item_dict = dict(zip(columns, row))
            
            # Converter Decimal para float para JSON
            if item_dict.get('KM'):
                item_dict['KM'] = float(item_dict['KM'])
            
            items.append(item_dict)
        
        cursor.close()
        return jsonify(items), 200
        
    except Exception as e:
        print(f"Erro ao buscar itens do evento: {str(e)}")
        import traceback
        traceback.print_exc()
        
        if 'cursor' in locals():
            cursor.close()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500


###############################

# Função corrigida para usar IDLOTE em vez de IDITEM
@app.route('/api/lote-inscricao-itens/<int:idlote>')
def get_lote_inscricao_itens(idlote):
    """API para obter dados de um lote específico para inscrição"""

    print(" ::::: DEBUG  def get_lote_inscricao ::::::")
    try:
        cur = mysql.connection.cursor()
        
        cur.execute("""
            SELECT 
              eil.IDLOTE,
              ei.IDITEM, 
              ei.DESCRICAO, 
              eil.VLINSCRICAO, 
              ROUND((eil.VLINSCRICAO * eil.PCTAXA / 100), 2) AS VLTAXA,
              ROUND(eil.VLINSCRICAO + (eil.VLINSCRICAO * eil.PCTAXA / 100), 2) AS VLTOTAL,
              (SELECT ROUND((ultimo.VLINSCRICAO / 2), 2) 
               FROM EVENTO_ITEM_LOTES ultimo 
               WHERE ultimo.IDLOTE = eil.IDITEM_ULTIMO_LOTE) AS VL_MEIA,
              (SELECT ROUND(((ultimo.VLINSCRICAO / 2) * ultimo.PCTAXA / 100), 2) 
               FROM EVENTO_ITEM_LOTES ultimo 
               WHERE ultimo.IDLOTE = eil.IDITEM_ULTIMO_LOTE) AS VL_TAXA_MEIA,
              (SELECT ROUND((ultimo.VLINSCRICAO / 2) + ((ultimo.VLINSCRICAO / 2) * ultimo.PCTAXA / 100), 2) 
               FROM EVENTO_ITEM_LOTES ultimo 
               WHERE ultimo.IDLOTE = eil.IDITEM_ULTIMO_LOTE) AS VL_TOTAL_MEIA,
              e.TITULO, e.IDEVENTO
            FROM EVENTO_ITEM_LOTES eil
            JOIN EVENTO_ITEM ei ON eil.IDITEM = ei.IDITEM
            JOIN EVENTO1 e ON ei.IDEVENTO = e.IDEVENTO
            WHERE eil.IDLOTE = %s
        """, (idlote,))
        
        lote_data = cur.fetchone()
        cur.close()
        
        if not lote_data:
            return jsonify({'error': 'Lote não encontrado'}), 404
        
        # Função para formatar valores em formato brasileiro (para uso na API também)
        def formatar_valor_brasileiro_api(valor):
            """Converte valor decimal para formato brasileiro (vírgula como separador decimal)"""
            if valor is None:
                return "0,00"
            return f"{float(valor):.2f}".replace('.', ',')
        
        return jsonify({
            'idevento': lote_data[10],  # IDEVENTO
            'idlote': lote_data[0],     # IDLOTE - novo campo
            'iditem': lote_data[1],     # IDITEM da tabela EVENTO_ITEM
            'titulo': lote_data[9],     # TITULO do evento
            'descricao': lote_data[2],  # DESCRICAO do item
            'vlinscricao': float(lote_data[3]) if lote_data[3] else 0,
            'vltaxa': float(lote_data[4]) if lote_data[4] else 0,
            'vltotal': float(lote_data[5]) if lote_data[5] else 0,
            'vlinscricao_meia': float(lote_data[6]) if lote_data[6] else 0,
            'vltaxa_meia': float(lote_data[7]) if lote_data[7] else 0,
            'vltotal_meia': float(lote_data[8]) if lote_data[8] else 0,
            # Valores formatados em padrão brasileiro para exibição
            'vlinscricao_formatada': formatar_valor_brasileiro_api(lote_data[3]),
            'vltaxa_formatada': formatar_valor_brasileiro_api(lote_data[4]),
            'vltotal_formatada': formatar_valor_brasileiro_api(lote_data[5]),
            'vlinscricao_meia_formatada': formatar_valor_brasileiro_api(lote_data[6]),
            'vltaxa_meia_formatada': formatar_valor_brasileiro_api(lote_data[7]),
            'vltotal_meia_formatada': formatar_valor_brasileiro_api(lote_data[8])
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro ao buscar dados do lote: {str(e)}'}), 500


# Se você ainda tem código JavaScript que chama a rota antiga com IDITEM, 
# mantenha também esta rota de compatibilidade:
@app.route('/api/lote-inscricao-item/<int:iditem>/<int:idlote>')
def get_lote_inscricao_por_item_e_lote(iditem, idlote):
    """API atualizada - busca lote específico pelo IDITEM e IDLOTE"""
    
    print(f" ::::: DEBUG get_lote_inscricao_por_item_e_lote - IDITEM: {iditem}, IDLOTE: {idlote} ::::::")
    try:
        cur = mysql.connection.cursor()
        
        # Busca o lote específico usando IDLOTE e IDITEM
        cur.execute("""
            SELECT 
              eil.IDLOTE,
              ei.IDITEM, 
              ei.DESCRICAO, 
              eil.VLINSCRICAO, 
              ROUND((eil.VLINSCRICAO * eil.PCTAXA / 100), 2) AS VLTAXA,
              ROUND(eil.VLINSCRICAO + (eil.VLINSCRICAO * eil.PCTAXA / 100), 2) AS VLTOTAL,
              (SELECT ROUND((ultimo.VLINSCRICAO / 2), 2) 
               FROM EVENTO_ITEM_LOTES ultimo 
               WHERE ultimo.IDLOTE = eil.IDITEM_ULTIMO_LOTE) AS VL_MEIA,
              (SELECT ROUND(((ultimo.VLINSCRICAO / 2) * ultimo.PCTAXA / 100), 2) 
               FROM EVENTO_ITEM_LOTES ultimo 
               WHERE ultimo.IDLOTE = eil.IDITEM_ULTIMO_LOTE) AS VL_TAXA_MEIA,
              (SELECT ROUND((ultimo.VLINSCRICAO / 2) + ((ultimo.VLINSCRICAO / 2) * ultimo.PCTAXA / 100), 2) 
               FROM EVENTO_ITEM_LOTES ultimo 
               WHERE ultimo.IDLOTE = eil.IDITEM_ULTIMO_LOTE) AS VL_TOTAL_MEIA,
              e.TITULO, e.IDEVENTO
            FROM EVENTO_ITEM_LOTES eil
            JOIN EVENTO_ITEM ei ON eil.IDITEM = ei.IDITEM
            JOIN EVENTO1 e ON ei.IDEVENTO = e.IDEVENTO
            WHERE eil.IDLOTE = %s
            AND ei.IDITEM = %s
        """, (idlote, iditem))
        
        lote_data = cur.fetchone()
        cur.close()
        
        if not lote_data:
            return jsonify({'error': 'Lote não encontrado para este item e lote'}), 404
        
        def formatar_valor_brasileiro_api(valor):
            if valor is None:
                return "0,00"
            return f"{float(valor):.2f}".replace('.', ',')
        
        return jsonify({
            'idevento': lote_data[10],
            'idlote': lote_data[0],
            'iditem': lote_data[1],
            'titulo': lote_data[9],
            'descricao': lote_data[2],
            'vlinscricao': float(lote_data[3]) if lote_data[3] else 0,
            'vltaxa': float(lote_data[4]) if lote_data[4] else 0,
            'vltotal': float(lote_data[5]) if lote_data[5] else 0,
            'vlinscricao_meia': float(lote_data[6]) if lote_data[6] else 0,
            'vltaxa_meia': float(lote_data[7]) if lote_data[7] else 0,
            'vltotal_meia': float(lote_data[8]) if lote_data[8] else 0,
            'vlinscricao_formatada': formatar_valor_brasileiro_api(lote_data[3]),
            'vltaxa_formatada': formatar_valor_brasileiro_api(lote_data[4]),
            'vltotal_formatada': formatar_valor_brasileiro_api(lote_data[5]),
            'vlinscricao_meia_formatada': formatar_valor_brasileiro_api(lote_data[6]),
            'vltaxa_meia_formatada': formatar_valor_brasileiro_api(lote_data[7]),
            'vltotal_meia_formatada': formatar_valor_brasileiro_api(lote_data[8])
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro ao buscar dados do lote: {str(e)}'}), 500


@app.route('/evento-inscricao/<int:idevento>')
def evento_inscricao(idevento):
    """Rota para servir a página de inscrição"""
    
    # TEMPORÁRIO: Comentar validação de token para teste
    # Depois você pode reativar quando o fluxo estiver funcionando
    """
    # Verificar se tem token válido na sessão
    token_esperado = session.get('inscricao_token')
    token_recebido = request.args.get('token')
    
    if not token_esperado or token_recebido != token_esperado:
        # Buscar dados do evento para redirect
        cur = mysql.connection.cursor()
        cur.execute('''
            SELECT CONCAT('evento','/',DSLINK) AS DSLINK FROM EVENTO1 WHERE IDEVENTO = %s
        ''', (idevento,))
        
        evento_redirect = cur.fetchone()
        cur.close()
        
        if evento_redirect and evento_redirect[0]:
            # Redirecionar para a página pública do evento usando DSLINK
            return redirect(f'/{evento_redirect[0]}')
        else:
            # Fallback para página principal se não encontrar o evento ou DSLINK
            return redirect('/')
    
    # Limpar o token da sessão (uso único)
    session.pop('inscricao_token', None)
    """
    
    # Buscar dados do evento
    cur = mysql.connection.cursor()
    
    try:
        # Query para dados básicos do evento
        cur.execute("""
            SELECT TITULO, DATAINICIO, HRINICIO, ENDERECO, CIDADEUF, CONCAT('evento','/',DSLINK) AS DSLINK 
            FROM EVENTO1 WHERE IDEVENTO = %s
        """, (idevento,))

        evento_data = cur.fetchone()
        
        if not evento_data:
            return "Evento não encontrado", 404

        # Preparar dados para o template
        evento = {
            'idevento': idevento,
            'titulo': evento_data[0],
            'data': evento_data[1],
            'hora': evento_data[2],
            'local': evento_data[3],
            'cidade_uf': evento_data[4],
            'dslink': evento_data[5]
        }

        # Criar response com CSP headers corretos
        response = make_response(render_template('evento_inscricao.html', evento=evento))
        
        # Adicionar cdnjs.cloudflare.com ao CSP para permitir jQuery
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
            "https://secure.mlstatic.com https://sdk.mercadopago.com https://*.mercadopago.com "
            "https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https:; "
            "font-src 'self' https://cdnjs.cloudflare.com;"
        )
        
        response.headers['Content-Security-Policy'] = csp
        
        return response
        
    except Exception as e:
        print(f"Erro ao carregar evento {idevento}: {str(e)}")
        return "Erro interno do servidor", 500
    finally:
        cur.close()


# ALTERNATIVA: Rota para gerar token de inscrição (se quiser manter o sistema de token)
@app.route('/gerar-token-inscricao/<int:idevento>')
def gerar_token_inscricao(idevento):
    """Gera token para acesso à página de inscrição"""
    import secrets
    
    # Gerar token único
    token = secrets.token_urlsafe(32)
    
    # Salvar na sessão
    session['inscricao_token'] = token
    session['idevento_token'] = idevento
    
    # Redirecionar para página de inscrição com token
    return redirect(f'/evento-inscricao/{idevento}?token={token}')

#################################################
# Rotas para gerenciamento de imagens do evento #
#################################################

# GET - Listar imagens do evento
@app.route('/api/eventos/<int:evento_id>/imagens', methods=['GET'])
def listar_imagens_evento(evento_id):
    """API para listar todas as imagens de um evento específico"""
    try:
        cursor = mysql.connection.cursor()
        query = """
            SELECT ID, IDEVENTO, TITULO_IMG, IMG
            FROM EVENTO_IMG 
            WHERE IDEVENTO = %s
            ORDER BY ID ASC
        """
        cursor.execute(query, (evento_id,))
        imagens = cursor.fetchall()
        cursor.close()
        
        # Converter para lista de dicionários
        imagens_list = []
        for imagem in imagens:
            imagem_dict = {
                'ID': imagem[0],
                'IDEVENTO': imagem[1],
                'TITULO_IMG': imagem[2],
                'IMG': base64.b64encode(imagem[3]).decode('utf-8') if imagem[3] else None
            }
            imagens_list.append(imagem_dict)
        
        print(f"Carregadas {len(imagens_list)} imagens para evento {evento_id}")  # Debug
        return jsonify(imagens_list)
        
    except Exception as e:
        print(f"Erro ao listar imagens do evento {evento_id}: {str(e)}")  # Debug
        return jsonify({'error': str(e)}), 500

# POST - Criar nova imagem
@app.route('/api/evento-imagens', methods=['POST'])  
def criar_imagem():
    """API para criar uma nova imagem do evento"""
    try:
        data = request.get_json()
        
        # Validações
        if not data.get('idevento'):
            return jsonify({'error': 'ID do evento é obrigatório'}), 400
            
        if not data.get('titulo_img'):
            return jsonify({'error': 'Título da imagem é obrigatório'}), 400
            
        if not data.get('img'):
            return jsonify({'error': 'Imagem é obrigatória'}), 400
        
        # Processar imagem base64
        img_data = data.get('img')
        if img_data.startswith('data:image'):
            # Remover o prefixo data:image/...;base64,
            img_data = img_data.split(',')[1]
        
        try:
            img_binary = base64.b64decode(img_data)
        except Exception as e:
            return jsonify({'error': 'Formato de imagem inválido'}), 400
        
        cursor = mysql.connection.cursor()
        query = """
            INSERT INTO EVENTO_IMG (IDEVENTO, TITULO_IMG, IMG) 
            VALUES (%s, %s, %s)
        """
        cursor.execute(query, (
            data['idevento'],
            data['titulo_img'],
            img_binary
        ))
        mysql.connection.commit()
        
        imagem_id = cursor.lastrowid
        cursor.close()
        
        print(f"Imagem criada com ID {imagem_id} para evento {data['idevento']}")  # Debug
        return jsonify({'message': 'Imagem criada com sucesso', 'id': imagem_id}), 201
        
    except Exception as e:
        print(f"Erro ao criar imagem: {str(e)}")  # Debug
        return jsonify({'error': str(e)}), 500

# PUT - Atualizar imagem existente
@app.route('/api/evento-imagens/<int:imagem_id>', methods=['PUT'])
def atualizar_imagem(imagem_id):
    """API para atualizar uma imagem existente"""
    try:
        data = request.get_json()
        
        # Verificar se a imagem existe
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT ID FROM EVENTO_IMG WHERE ID = %s", (imagem_id,))
        if not cursor.fetchone():
            cursor.close()
            return jsonify({'error': 'Imagem não encontrada'}), 404
        
        # Preparar query de atualização dinamicamente
        campos_atualizacao = []
        valores = []
        
        if data.get('titulo_img'):
            campos_atualizacao.append("TITULO_IMG = %s")
            valores.append(data['titulo_img'])
        
        if data.get('img'):
            # Processar nova imagem
            img_data = data.get('img')
            if img_data.startswith('data:image'):
                img_data = img_data.split(',')[1]
            
            try:
                img_binary = base64.b64decode(img_data)
                campos_atualizacao.append("IMG = %s")
                valores.append(img_binary)
            except Exception as e:
                cursor.close()
                return jsonify({'error': 'Formato de imagem inválido'}), 400
        
        if not campos_atualizacao:
            cursor.close()
            return jsonify({'error': 'Nenhum campo para atualizar'}), 400
        
        # Executar atualização
        valores.append(imagem_id)
        query = f"UPDATE EVENTO_IMG SET {', '.join(campos_atualizacao)} WHERE ID = %s"
        cursor.execute(query, valores)
        mysql.connection.commit()
        cursor.close()
        
        print(f"Imagem {imagem_id} atualizada com sucesso")  # Debug
        return jsonify({'message': 'Imagem atualizada com sucesso'}), 200
        
    except Exception as e:
        print(f"Erro ao atualizar imagem {imagem_id}: {str(e)}")  # Debug
        return jsonify({'error': str(e)}), 500

# DELETE - Excluir imagem
@app.route('/api/evento-imagens/<int:imagem_id>', methods=['DELETE'])
def excluir_imagem(imagem_id):
    """API para excluir uma imagem do evento"""
    try:
        cursor = mysql.connection.cursor()
        
        # Verificar se a imagem existe
        cursor.execute("SELECT ID FROM EVENTO_IMG WHERE ID = %s", (imagem_id,))
        if not cursor.fetchone():
            cursor.close()
            return jsonify({'error': 'Imagem não encontrada'}), 404
        
        # Excluir a imagem
        cursor.execute("DELETE FROM EVENTO_IMG WHERE ID = %s", (imagem_id,))
        mysql.connection.commit()
        cursor.close()
        
        print(f"Imagem {imagem_id} excluída com sucesso")  # Debug
        return jsonify({'message': 'Imagem excluída com sucesso'}), 200
        
    except Exception as e:
        print(f"Erro ao excluir imagem {imagem_id}: {str(e)}")  # Debug
        return jsonify({'error': str(e)}), 500


###############################

###############################


# Rota para listar inscrições
@app.route('/api/inscricoes', methods=['GET'])
def listar_inscricoes():
    """API para listar inscrições por status"""
    try:
        fl_vlenviado = request.args.get('fl_vlenviado', 'N')
        
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT ei.IDINSCRICAO, ei.IDITEMEVENTO, i.DESCRICAO AS MODALIDADE, 
                   CONCAT(ei.NOME,' ' ,ei.SOBRENOME) NOME_COMPLETO, 
                   ei.IDADE, ei.SEXO, 
                   ei.DTPAGAMENTO, 
                   ei.VLINSCRICAO, ei.VLPAGO, ei.VLLIQUIDO, ei.VLCREDITO, ei.FL_VLENVIADO
            FROM EVENTO_INSCRICAO ei
            INNER JOIN EVENTO_ITEM i ON i.IDITEM = ei.IDITEMEVENTO
            WHERE ei.FL_VLENVIADO = %s
            AND ei.STATUS = 'A'
            ORDER BY ei.IDINSCRICAO
        """, (fl_vlenviado,))
        
        inscricoes = []
        for row in cursor.fetchall():
            # Converter data para string se não for None
            dtpagamento = row[6].strftime('%Y-%m-%d') if row[6] else None
            
            inscricoes.append({
                'IDINSCRICAO': row[0],
                'IDITEMEVENTO': row[1],
                'MODALIDADE': row[2],
                'NOME_COMPLETO': row[3],
                'IDADE': row[4],
                'SEXO': row[5],
                'DTPAGAMENTO': dtpagamento,
                'VLINSCRICAO': float(row[7]) if row[7] else 0.0,
                'VLPAGO': float(row[8]) if row[8] else 0.0,
                'VLLIQUIDO': float(row[9]) if row[9] else 0.0,
                'VLCREDITO': float(row[10]) if row[10] else 0.0,
                'FL_VLENVIADO': row[11]
            })
        
        cursor.close()
        return jsonify(inscricoes)
        
    except Exception as e:
        return jsonify({'error': f'Erro ao carregar inscrições: {str(e)}'}), 500
    

# Rota para confirmar envio de valores
@app.route('/api/inscricoes/confirmar-envio', methods=['PUT'])
def confirmar_envio_valores():
    """API para atualizar FL_VLENVIADO para 'S'"""
    try:
        data = request.get_json()
        ids = data.get('ids', [])
        
        if not ids:
            return jsonify({'error': 'Lista de IDs é obrigatória'}), 400
        
        cursor = mysql.connection.cursor()
        
        # Construir query para update múltiplo
        placeholders = ','.join(['%s'] * len(ids))
        query = f"""
            UPDATE EVENTO_INSCRICAO 
            SET FL_VLENVIADO = 'S'
            WHERE IDINSCRICAO IN ({placeholders})
        """
        
        cursor.execute(query, ids)
        mysql.connection.commit()
        
        rows_affected = cursor.rowcount
        cursor.close()
        
        return jsonify({
            'success': True,
            'message': f'{rows_affected} inscrição(ões) atualizada(s) com sucesso!',
            'updated_count': rows_affected
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro ao confirmar envio: {str(e)}'}), 500


@app.route("/adm/eventos")
def adm_eventos():
    return render_template("adm_eventos.html")




if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)


















