import mysql.connector
import sqlite3
import smtplib
import email.message
import random
import os
from dotenv import load_dotenv
from mysqlconnect import mysql_db
from funcoes import enviar_email, calculateAge, lista_estados, lista_forma_pagamento
from flask import Flask, render_template, redirect, request, jsonify, flash
#from flask_mysqldb import MySQL
from datetime import date, datetime
from apimercadopago import gera_link_pagamento, gerar_pagamento_pix
import mercadopago 

load_dotenv(override=True)

secret_key = os.getenv('SECRET_KEY')
sdk_value = os.getenv('SDK_KEY')
#db_host = os.getenv('DB_HOST')
#db_user = os.getenv('DB_USER')
#db_password = os.getenv('DB_PASSWORD')
#db_name = os.getenv('DB_NAME')

sdk = mercadopago.SDK(sdk_value)


ecmrundb = mysql_db()

app = Flask(__name__)
app.config["SECRET_KEY"] = secret_key

gl_cpf = ""
gl_email = ""
gl_prova = ""
gl_idprova = 0
gl_idatleta = 0
gl_nome = ""
gl_sobrenome = ""
gl_nascimento = ""
gl_idade = ""
gl_sexo = ""
gl_celular = ""
gl_cidade = ""
gl_uf = ""
gl_equipe = ""

#formapgtos = ["Dinheiro","PIX","Cartão de Crédito"]

def fn_cpf(var_cpf):
    global gl_cpf
    a = var_cpf
    b = ".-"
    for i in range(0,len(b)):
        a = a.replace(b[i],"")
    gl_cpf =  a

def fn_prova(var1):
    global gl_prova
    gl_prova = var1

def fn_idprova(var1):
    global gl_idprova
    gl_idprova = var1

def fn_email(var_email):
    global gl_email
    gl_email = var_email

def fn_idatleta(var_id):
    global gl_idatleta
    gl_idatleta = var_id

def fn_nome(var1):
    global gl_nome
    gl_nome = var1

def fn_sobrenome(var1):
    global gl_sobrenome
    gl_sobrenome = var1

def fn_celular(var1):
    global gl_celular
    gl_celular = var1

def fn_nascimento(var1):
    global gl_nascimento
    gl_nascimento = var1

def fn_sexo(var1):
    global gl_sexo
    gl_sexo = var1

def fn_cidade(var1):
    global gl_cidade
    gl_cidade = var1

def fn_uf(var1):
    global gl_uf
    gl_uf = var1

def fn_equipe(var1):
    global gl_equipe
    gl_equipe = var1

@app.route("/")
def home():
    return render_template("home.html")

#@app.route("/macaxeirabackyard", methods=["POST"])

@app.route("/macaxeirabackyard", methods=["GET"])
def macaxeirabackyard():
    return render_template("mbu.html")

@app.route('/teste')
def teste():
    return render_template('teste.html')

@app.route('/teste2')
def teste2():
    return render_template('teste2.html')
    
@app.route('/mbu', methods=["POST"])
def mbu():

    v_cpf = request.form.get("cpf")
    v_email = request.form.get("email")
    v_prova = request.form.get("prova")

    fn_cpf(v_cpf)
    fn_email(v_email)
    fn_prova(v_prova)   

    print(gl_cpf) 
    print(gl_prova) 


    cursor =  ecmrundb.cursor()
    sql = f'SELECT NRINSCRICAO, IDATLETA, CPF, NOME, SOBRENOME FROM ecmrun.VW_ATLETA WHERE CPF = "{gl_cpf}"'
    cursor.execute(sql)
    resultado = cursor.fetchone() 

    if resultado: # Se ja tiver inscrito
        cpf = resultado[2]
        nome = resultado[3]
        # Exibir os valores
        print("CPF:", cpf)
        print("Nome:", nome)

        flash("Já consta inscrição para o e-mail informado!")
        return redirect("/macaxeirabackyard")        

    else:  # Se não tiver inscrito

        cursor =  ecmrundb.cursor()
        sql = f'SELECT IDATLETA, CPF, NOME, SOBRENOME, DTNASCIMENTO, NRCELULAR, SEXO, CIDADE, UF, EQUIPE FROM ecmrun.ATLETA WHERE CPF = "{gl_cpf}"'
        cursor.execute(sql)
        dados = cursor.fetchone() 
        print("CPF da PEsquisa:", gl_cpf)
        
        if dados:  # se ja existe cadastro do atleta
            idatleta = dados[0]
            cpf = dados[1]
            nome = dados[2]
            sobrenome = dados[3]
            dtnasc = dados[4]
            celular = dados[5]
            sexo = dados[6]
            cidade = dados[7]
            estado = dados[8]
            data1 = dtnasc[6:10] +'-'+ dtnasc[3:5]+'-'+ dtnasc[0:2]
            cel = '('+dados[5][0:2] +') '+ dados[5][2:7]+'-'+ dados[5][7:11]

            fn_idatleta(idatleta)
            fn_nome(dados[2])
            fn_sobrenome(dados[3])
            fn_nascimento(dados[4])
            fn_celular(dados[5])
            fn_sexo(dados[6])
            fn_cidade(dados[7])
            fn_uf(dados[8])
            fn_equipe(dados[9])

            # Exibir os valores
            print("CPF:", cpf)
            print("Nome:", nome)
            print("SObreNome:", sobrenome)
            print("Nasc:", dtnasc)
            print("Celular:", celular)
            print("Sexo:", sexo)
            print("Cidade:", cidade)
            print("Estado:", estado)
            print("Data1:", data1)
            
        else: # Se NÃO existe cadastro do atleta

            fn_idatleta(0) # se o 'idatleta' for 0, o programa adiciona no cadastrdo a atleta na route  '/confirmar' 

            #dados = None
            data1 = None
            cel = ""
            estado = "RO"
            #dados[6] = "M"

        return render_template('formulario.html', dados=dados,datanasc=data1, celular1=cel, estados=lista_estados(),
                               estado_selecionado=estado, formapgtos=lista_forma_pagamento())

    # Fechar o cursor e a conexão
    cursor.close()
    ecmrundb.close()

@app.route('/confirmado')
def confirmado():
    return render_template('confirmado.html')


@app.route('/confirmar', methods=["POST"])
def confirmar():
    fn_nome(request.form.get("nome").strip())
    fn_sobrenome(request.form.get("sobrenome").strip())
    v_dtnasc = request.form.get("datanascimento")
    v_telefone = request.form.get("telefone")
    fn_sexo(request.form.get("sexo"))
    camiseta = request.form.get("camiseta")
    fn_cidade(request.form.get("cidade"))
    fn_uf(request.form.get("estado"))
    fn_equipe(request.form.get("equipe"))
    formapgto = request.form.get("formapagamento")

    #retira os caracteres e espacos do telefone 
    ncelular = v_telefone
    crtr1 = '() -'
    for i in range(0,len(crtr1)):
        ncelular = ncelular.replace(crtr1[i],"")
    # --

    idade = calculateAge(str(v_dtnasc))

    dataatual = date.today()
    datainscricao = dataatual.strftime("%d/%m/%Y")

    datanasc_str = str(v_dtnasc) #datetime.strpfime(v_dtnasc, "%Y-%m-%d") 2024-08-17
    datanasc_str = datanasc_str[8:10]+'/'+datanasc_str[5:7]+'/'+datanasc_str[0:4]

    if gl_prova == "Principal":
        idprova = 1
        if idade < 60:
            vl = 279
            #fn_idpgto(1)
        else:
            vl = 139.5
            #fn_idpgto(2)
    else:
        idprova = 2
        if idade < 60:
            vl = 179
            #fn_idpgto(3)
        else:
            vl = 89.5
            #fn_idpgto(4)

    vl_inscricao = vl

    print("Forma Pgto:", formapgto)

    if gl_idatleta == 0:

        sql = f"""INSERT INTO ecmrun.ATLETA ( 
                  CPF, NOME, SOBRENOME, DTNASCIMENTO, NRCELULAR, SEXO, EMAIL, CIDADE, UF, ATIVO, EQUIPE)
                VALUES (
                  "{gl_cpf}", upper("{gl_nome}"), upper("{gl_sobrenome}"), "{datanasc_str}", "{ncelular}", "{gl_sexo}",
                  "{gl_email}", "{gl_cidade}", "{gl_uf}", "S", "{gl_equipe}") """
                        

        cursorA =  ecmrundb.cursor()
        cursorA.execute(sql)
        ecmrundb.commit()
        cursorA.close()

        cursor =  ecmrundb.cursor()
        sql2 = f'SELECT IDATLETA, CPF FROM ecmrun.ATLETA WHERE CPF = "{gl_cpf}"'
        cursor.execute(sql2)
        dados1 = cursor.fetchone() 
        print("CPF da PEsquisa:", gl_cpf)
        
        if dados1:  # se ja existe cadastro do atleta
            idatleta1 = dados1[0]
            fn_idatleta(idatleta1)
        else:
            print("Atleta não foi cadastrado, verifique")
       
    else:

        sql = f"""UPDATE ecmrun.ATLETA SET 
                    CPF = "{gl_cpf}", 
                    NOME = "{gl_nome}", 
                    SOBRENOME = "{gl_sobrenome}", 
                    DTNASCIMENTO = "{datanasc_str}", 
                    NRCELULAR = "{ncelular}", 
                    SEXO = "{gl_sexo}", 
                    EMAIL = "{gl_email}", 
                    CIDADE = "{gl_cidade}", 
                    UF = "{gl_uf}",  
                    EQUIPE = "{gl_equipe}"
                 WHERE IDATLETA = {gl_idatleta} """

        cursorA =  ecmrundb.cursor()
        cursorA.execute(sql)
        ecmrundb.commit()
        cursorA.close()

    sql1 = f"""INSERT INTO ecmrun.BACKYARD2025 (
                 IDATLETA, IDADE, CAMISETA, PROVA, IDPROVA, VLINSCRICAO, VLPAGO, FORMAPAGTO, CONFIRMADO,
                 EMAILENVIADO, DTINSCRICAO, ACEITO_TERMO)
               VALUES (
                 {gl_idatleta}, {idade}, "{camiseta}", "{gl_prova}", {idprova}, {vl_inscricao}, 0.00,
                 "{formapgto}", "N", "N", "{datainscricao}", "") """

    cursorB =  ecmrundb.cursor()
    cursorB.execute(sql1)
    ecmrundb.commit()
    cursorB.close()

    title = "Inscrição Macaxeira Backyard"
    quantity = 1  # Defina a quantidade desejada
    unit_price = 0.99  # Defina o preço unitário desejado

    link_iniciar_pagto = gerar_pagamento_pix(title, quantity, unit_price)
    #return render_template("formulario.html", link_pagamemto=link_iniciar_pagto)
    return render_template("confirmado.html", link_pagamemto=link_iniciar_pagto)


    #return render_template('confirmado.html')



@app.route('/sucesso')
def sucesso():
    return "Pagamento realizado com sucesso!"

@app.route('/falha')
def falha():
    return "O pagamento falhou."

@app.route('/pendente')
def pendente():
    return "O pagamento está pendente."


@app.route("/webhook", methods=["POST"])
def webhook():
    # Recebe a notificação do Mercado Pago
    data = request.json

    # Verifica se a notificação é válida
    if data and "data" in data:
        payment_id = data["data"]["id"]
        payment_status = data["data"]["status"]

        # Aqui você pode processar o status do pagamento
        # Por exemplo, atualizar o banco de dados ou enviar um e-mail
        print(f"Pagamento ID: {payment_id}, Status: {payment_status}")

        # Retorna uma resposta 200 OK para o Mercado Pago
        return jsonify({"status": "received"}), 200
    else:
        return jsonify({"error": "Invalid data"}), 400



if __name__ == "__main__":
    app.run(debug=True, port=5000)

