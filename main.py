from menu_management import Waiter
from llm.gpt import chat
from function import func_list
import json

dish_list = Waiter('data/menu.xlsx')

system_prompt = {
    "role":"system",
    "content": '''As a helpful waiter, your job responsibilities include recording the customers' meal choices and guiding them on which dishes they need. You should follow the following rules:
1, In general, your job responsibilities include following the service process, introducing dishes, verifying orders, recording orders, confirming bills with customers, and processing payments.
2, When you are unable to confirm the specific dish the customer wants, you MUST to verify with the customer. For example, if the customer requests a "burger" but there are options for chicken burger and beef burger, please ask the customer, "Do you prefer chicken or beef?" to clarify their preference.
3, Please use casual Chinese and keep your responses concise when interacting with customers.
4, REPEAT!!! When you are unable to confirm the specific dish the customer wants, you MUST to verify with the customer.'''
}

# 修改一波list，这样子只要进行了append，就会自动输出对应的内容
class VerboseList(list):
    def append(self, item):
        print(item)
        super().append(item)


imformation = VerboseList()
imformation.append(system_prompt)
#imformation.append({"role": "function", "name": "get_meal", "content": "{\"hint\": \"找到多种客户可能需要的菜品，请你向客户确认需要哪一种\\n注意：如果接下来客户讲述的时候，无法决定具体是哪个菜品，请你向客户主动询问!!!\", \"meals\": [{\"type\": \"奶茶\", \"name\": \"布丁奶茶\", \"price\": 7, \"appendix\": NaN}, {\"type\": \"奶茶\", \"name\": \"双拼奶茶\", \"price\": 7, \"appendix\": \"主辅料为:鸡蛋布丁，珍珠\"}, {\"type\": \"奶茶\", \"name\": \"椰果奶茶\", \"price\": 7, \"appendix\": NaN}, {\"type\": \"奶茶\", \"name\": \"珍珠奶茶\", \"price\": 6, \"appendix\": NaN}, {\"type\": \"奶茶\", \"name\": \"原味奶茶\", \"price\": 6, \"appendix\": NaN}]}"})


while True:
    text = input('顾客:')
    new_chat = {"role": "user", "content": text}
    imformation.append(new_chat)

    while True:
        response = chat(list(imformation), func_list)

        # str格式代表直接有回复
        if isinstance(response, str):
            imformation.append({"role": "assistant", "content": str(response)})
            print(response)
            break

        # 读取原始输出，然后这里面GPT还有一点bug，要删掉两个部分的数据
        raw_answer = response[-1].dict()
        raw_answer['content'] = ''
        del raw_answer['function_call']

        response = response[:-1]
        imformation.append(raw_answer)

        # 否则就是列表，是函数
        for command, id in zip(response, raw_answer['tool_calls']):
            name = command[:command.find('(')]
            try:
                function_return = eval('dish_list.' + command)
            except Exception as e:
                function_return = '调用出错，请重新发送命令'
            function_return = {"role": "tool", "tool_call_id": id['id'], "name": name, "content": str(function_return)}
            imformation.append(function_return)