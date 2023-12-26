#本代码为系统与GPT进行交互的封装接口
#该代码需在梯子环境下运行
from openai import OpenAI
import json
import httpx
import os


OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
client = OpenAI(
    api_key=OPENAI_API_KEY,
    http_client=httpx.Client(
        proxies="http://127.0.0.1:7890"
    )
)

#与ChatGPT进行对话的模块
#返回的两个变量，第一个是返回说的话(或者所需函数的eval表达式), 另一个是完整的调用信息
def chat(prompt, function_list=None, temperature = 0.3):
    if isinstance(prompt, list):
        messages = prompt
    else:
        messages = [{"role": "user", "content": prompt}]

    function_list = [{"type":"function", "function": func} for func in function_list] if function_list is not None else None

    completion = client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        messages=messages,
        tools= function_list,
        temperature=temperature
    )

    # 如果直接说话，就直接返回
    answer = completion.choices[0].message.content
    if answer != None:
        return answer

    # 把function_call中输出的信息，直接变为可以eval执行的python代码
    def convert_to_eval(call_dict):
        function_name = call_dict['name']
        arguments_dict = json.loads(call_dict['arguments'])
        arguments = [str(key) + '=' + json.dumps(value, ensure_ascii=False) for key, value in arguments_dict.items()]
        return function_name + '(' + ','.join(arguments) + ')'

    # 否则输出函数调用的情况
    answer = [ convert_to_eval(call.function.dict()) for call in completion.choices[0].message.tool_calls]
    answer.append(completion.choices[0].message)
    return answer

#基于ChatGPT求embedding的模块
def embedding(prompt):
    completion = client.embeddings.create(
        model = 'text-embedding-ada-002',
        input = prompt
    )
    return completion.data[0].embedding