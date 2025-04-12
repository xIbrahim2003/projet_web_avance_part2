README  concernant le SHOP/PAY API

Modification importante dans l'API :
Le point d'accès POST /shop/pay a été remplacé par POST /order/{order_id}/shops/pay**.

Détails de la modification :
La nouvelle route /order/{order_id}/shops/pay permet d'effectuer un paiement pour une commande spécifique identifiée par son "order_id".
Comme le Put order/order_id (suivi du json de la carte de crédit) mais les valeurs retournées ne sont pas les meme entre le put et le post.


 


