import smtplib
import email.message
import os
from datetime import date, datetime


def lista_forma_pagamento():
    fmpgto = {'Dinheiro','PIX','Cartão de Crédito'}
    return fmpgto

def lista_estados():
    estados = {
        'AC': 'Acre',
        'AL': 'Alagoas',
        'AP': 'Amapá',
        'AM': 'Amazonas',
        'BA': 'Bahia',
        'CE': 'Ceará',
        'DF': 'Distrito Federal',
        'ES': 'Espírito Santo',
        'GO': 'Goiás',
        'MA': 'Maranhão',
        'MT': 'Mato Grosso',
        'MS': 'Mato Grosso do Sul',
        'MG': 'Minas Gerais',
        'PA': 'Pará',
        'PB': 'Paraíba',
        'PR': 'Paraná',
        'PE': 'Pernambuco',
        'PI': 'Piauí',
        'RJ': 'Rio de Janeiro',
        'RN': 'Rio Grande do Norte',
        'RS': 'Rio Grande do Sul',
        'RO': 'Rondônia',
        'RR': 'Roraima',
        'SC': 'Santa Catarina',
        'SP': 'São Paulo',
        'SE': 'Sergipe',
        'TO': 'Tocantins'
    }
    
    return estados


def calculateAge(birthDate): 

    data_str = "2025-02-22"
    dataRef = datetime.strptime(data_str, "%Y-%m-%d")
    datanasc = datetime.strptime(birthDate, "%Y-%m-%d")

    age = dataRef.year - datanasc.year - ((dataRef.month, dataRef.day) < (datanasc.month, datanasc.day)) 
  
    return age 

def enviar_email(s_codigo, s_email): 
    try: 
        corpo_email = f"""
        <p>Inscrição - Macaxeira Backyard Ultra - 2ª Edição</p>
        <p><b>Código de Autenticação</b> </p>
        <p>Seu Código é: <h1><b>{s_codigo}</b></h1></p>
        """
        
        msg = email.message.Message()
        msg['Subject'] = F"""CÓDIGO DE VALIDAÇÃO - {s_codigo} """
        msg['Name'] = 'ECM RUN';
        msg['From'] = 'ecmsistemasdeveloper@gmail.com'
        msg['To'] = s_email
        password = 'mwxncuvjvmvwvnhp' 
        msg.add_header('Content-Type', 'text/html')
        #msg.attach()
        msg.set_payload(corpo_email)

        s = smtplib.SMTP('smtp.gmail.com: 587')
        s.starttls()
        # Login Credentials for sending the mail
        s.login(msg['From'], password)
        s.sendmail(msg['From'], [msg['To']], msg.as_string().encode('utf-8'))
        s.quit()
        resultado = "exito"
    except Exception as e:
        print("Erro")
        resultado = "falha"
    #finally:            
    return resultado
