import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
from flask import Flask, render_template, render_template_string,  redirect, request, jsonify, flash

__cnx = None

app = Flask(__name__)

load_dotenv(override=True)

db_host = os.getenv('DB_HOST')
db_user = os.getenv('DB_USER')
db_password = os.getenv('DB_PASSWORD')
db_name = os.getenv('DB_NAME')

def mysql_db():
    connection = None
    try:
        connection = mysql.connector.connect(
            host=db_host,
            user=db_user,
            password=db_password,
            database=db_name
        )
        print("Conexão com o banco de dados bem-sucedida")
    except Error as e:
        print(f"Erro: {e}")
    return connection    


 #   config = {
 #   'user': db_user,
 #   'password': db_password,
 #   'host': db_host,
 #   'port': '3306',
 #   'database': db_name,
 #   'raise_on_warnings': True,}
 #
 #   cnx = mysql.connector.connect(**config)    
 #   
 #   return cnx