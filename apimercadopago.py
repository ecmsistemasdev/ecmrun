import mercadopago
import datetime

#sdk = mercadopago.SDK("TEST-4419840842819511-121317-7e33f7a3784caf3948c6c3638355b36a-96531112")
sdk = mercadopago.SDK("APP_USR-4419840842819511-121317-8c522deb54aff8ea290465f557bcdf0b-96531112")

def gerar_pagamento_pix(title, quantity, unit_price):
    # Define os dados do pagamento

    payment_data = {
        "items": [
            {"id": "1", 
             "title": title, 
             "quantity": quantity, 
             "currency_id": "BRL", 
             "unit_price": unit_price}],
        "back_urls": {
            "success": "http://ecmrun.com.br/sucesso",
            "failure": "http://ecmrun.com.br/falha",
            "pending": "http://ecmrun.com.br/penndente",
        },
        "payment_method_id": "pix"
    }

    # Cria o pagamento
    result = sdk.payment().create(payment_data)

    # Obtém a resposta do pagamento
    payment = result["response"]
    link_iniciar_pagamento = payment["init_point"]

    return link_iniciar_pagamento




def gera_link_pagamento(title, quantity, unit_price): 
    payment_data = {
        "items": [
            {"id": "1", 
            "title": title ,
            "quantity": quantity, 
            "currency_id": "BRL", 
            "unit_price": unit_price
            }
        ],
        "back_urls": {
            "success": "http://ecmrun.com.br/aprovado",
            "failure": "http://ecmrun.com.br/negado",
            "pending": "http://ecmrun.com.br/negado",
        },
        "auto_return":"all"
    }

    result = sdk.preference().create(payment_data)
    payment = result["response"]
    link_iniciar_pagamento = payment["init_point"]

    return link_iniciar_pagamento

