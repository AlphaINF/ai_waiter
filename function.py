
# 菜品查询函数
get_meal_func = {
    "name": "get_meal",
    "description": "Allow you to search meals through names, descriptions, ingredients, prices, etc.",
    "parameters": {
        "type": "object",
        "properties": {
            "meal_description": {
                "type": "string",
                "description": "descriptions and details about the meal, including names, descriptions, ingredients, prices, etc. If customer has some special demand (e.g: he don't know what he need or meat but not chicken), you can enter in it too."
            }
        },
        "required": [
            "meal_description"
        ]
    }
}

# 物品查询函数
get_tableware_func = {
    "name": "get_tableware",
    "description": "Allow you to search tableware through name",
    "parameters": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "descriptions and details about the tableware"
            }
        },
        "required": [
            "name"
        ]
    }
}

# 操作订单管理系统的函数
order_management_func = {
    "name": "order_management",
    "description": "Allow you to add, edit, delete and generate invoices through the customer's instruction.\nPlease ensure that the selected dishes are unique, and if there are any questions, please ask the customer first.",
    "parameters": {
        "type": "object",
        "properties": {
            "operation_type": {
                "type": "string",
                "description": "Add means customer wants some meal, and system will add it into cart.\nDelete means delete someone.\nEdit means customer want to change the number of the meals.\nCheckout means customer has finished ordering and you should show him the bill.\nPayment means customer has confirmed the bill and needs to pay for the order",
                "enum": [
                    "add",
                    "delete",
                    "edit",
                    "checkout",
                    "payment"
                ]
            },
            "meal_name": {
                "type": "string",
                "description": "the meal that customer wants, you must enter full name(include bracket)"
            },
            "quantity": {
                "type": "number",
                "description": "Quantities of meals to add, delete or edit"
            }
        },
        "required": [
            "operation_type"
        ]
    }
}
