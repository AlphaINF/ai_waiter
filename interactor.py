from menu_management import Waiter
from llm.gpt import chat
from function import func_list

dish_list = Waiter('data/menu.xlsx')

system_prompt = {
    "role":"system",
    "content": '''你是一个餐馆的服务员，这个餐馆出售奶茶，冰淇淋和咖啡，你负责用插件查询和记录客户点下的菜品及所需的用餐工具，以及必要时呼叫店长，你的职责如下:
1. 你的职责包括: 向客户介绍，确认和记录菜品，查询订单的情况，必要时呼叫上级等
2. 当客户需要菜品或者需要用餐工具时，请你先调用插件查询是否有这一菜品或工具，再回答客户或操作订单系统
3. 当你无法通过现有信息确认客户的具体需求时，你必须主动向用户进行确认，比如说，客户表示需要"汉堡",但菜谱上有牛肉和猪肉汉堡，请你向客户询问"要猪肉的还是牛肉的"'''
}

# 修改一波list，这样子只要进行了append，就会自动输出对应的内容
class VerboseList(list):
    def append(self, item):
        print(item)
        super().append(item)


imformation = VerboseList()
imformation.append(system_prompt)

# 控制是否禁止调用函数的模块
function_mask = False

def get_response(text):
    global function_mask, imformation, dish_list

    print('顾客:', text)
    new_chat = {"role": "user", "content": text}
    imformation.append(new_chat)

    while True:
        response = chat(list(imformation), None if function_mask else func_list)
        function_mask = False

        # str格式代表直接有回复
        if isinstance(response, str):
            imformation.append({"role": "assistant", "content": str(response)})
            print('AI:', response)
            return response
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

            # 控制下一轮对话中临时屏蔽函数调用
            if 'mask' in function_return:
                function_mask = function_return['mask']
                del function_return['mask']
            function_return = {"role": "tool", "tool_call_id": id['id'], "name": name, "content": str(function_return)}
            imformation.append(function_return)