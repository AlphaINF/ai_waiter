
from llm.gpt import embedding, chat
import os
from tqdm import tqdm
import pickle
import numpy as np
import json

class menu:

    # 初始化
    # 如果菜品没有建立索引，则会自动建立
    def __init__(self, filename):
        import pandas as pd
        df = pd.read_excel(filename)

        self.__list_id = df['编号'].tolist()
        self.__list_type = df['类别'].tolist()
        self.__list_name = df['名称'].tolist()
        self.__list_price = df['价格'].tolist()
        self.__list_notes = df['备注'].tolist()

        self.__order = {}
        self.__len = len(self.__list_id)

        embedding_cache_filename = filename.replace('.xlsx', '.embe')
        if os.path.exists(embedding_cache_filename):
            with open(embedding_cache_filename, 'rb') as f:
                self.__embedding_list = pickle.load(f)
        else:
            self.__embedding_list = []
            for i in tqdm(range(self.__len)):
                keyword = ';'.join([str(self.__list_type[i]), str(self.__list_name[i]), str(self.__list_notes[i])])
                embe = embedding(keyword)
                self.__embedding_list.append(embe)
            self.__embedding_list = np.array(self.__embedding_list).astype(np.float32)

            with open(embedding_cache_filename, 'wb') as f:
                pickle.dump(self.__embedding_list, f)

    # 菜品的粗筛系统
    def __embedding_search(self, instruction):
        target_embedding = np.array(embedding(instruction)).astype(np.float32)
        cos_sims = self.__embedding_list.dot(target_embedding).tolist()

        permutation = [i for i in range(self.__len)]
        permutation = sorted(permutation, key = lambda x:cos_sims[x], reverse=True)
        name_list = [(i, cos_sims[i]) for i in permutation]

        return name_list

    #基于向量检索实现粗筛，随后由该模块进行精筛，选出符合条件的菜，返回其ID
    def __accurate_search(self, instruction):
        prompt_template = '''现在有一道菜，它的特征如下:
```
{}
```

现在用户表示，它需要的菜的特征为:
```
{}
```

请你判断该菜是否符合用户的要求。
请注意：特征可能是别名，请注意处理别名。
如果符合请你输出True，否则输出False'''
        name_list = self.__embedding_search(instruction)

        import concurrent.futures

        # 定义一个线程工作函数
        def thread_work(i):
            id = name_list[i][0]
            meal_trait_str = '类别:{}\n名称:{}\n价格:{}\n备注:{}'.format(self.__list_type[id], self.__list_name[id], self.__list_price[id], self.__list_notes[id])
            prompt = prompt_template.format(meal_trait_str, instruction)
            output = chat(prompt)
            if 'True' in output:
                return id
            else:
                return None

        # 初始化空列表
        answer_list = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_id = {executor.submit(thread_work, i): i for i in range(5)}
            for future in concurrent.futures.as_completed(future_to_id):
                id = future.result()
                if id is not None:
                    answer_list.append(id)

        return answer_list

    #输入一段meal_id, 输出对应的json
    def __get_meal_json(self, meal_list):
        output = []
        for id in meal_list:
            meal = {
                'type': self.__list_type[id],
                'name': self.__list_name[id],
                'price': self.__list_price[id]
            }
            if self.__list_notes:
                meal['appendix'] = self.__list_notes[id]

            output.append(meal)

        return output

    def __output_prompt_by_length(self, length):
        if length == 0:
            return '未找到符合条件的菜品，请向客户说明'
        if length == 1:
            return '已找到唯一的菜品，如果客户明确表示需要这款产品，请直接调用点菜插件将其加入订单，否则请向客户介绍本餐厅存在该菜品'
        if length > 1:
            return '找到多种客户可能需要的菜品，请你向客户确认需要哪一种\n注意：如果接下来客户讲述的时候，无法决定具体是哪个菜品，请你向客户主动询问!!!'

    def get_meal(self, meal_description):
        output = {}
        meal_id_list = self.__accurate_search(meal_description)
        output['hint'] = self.__output_prompt_by_length(len(meal_id_list))
        output['meals'] = self.__get_meal_json(meal_id_list)
        return output

    def order_management(self, operation_type=None, meal_name=None, quantity=None):

        if meal_name == '\n':
            print('err')

        output = {}
        if operation_type is None:
            output['error'] = '必须包含operation_type字段'
            return output

        if operation_type not in ["add", "delete", "edit", "checkout", "payment"]:
            output['error'] = 'operation_type字段不合法'
            return output

        if operation_type in ["add", "delete", "edit"]:

            if meal_name is None:
                output['error'] = '使用' + operation_type + '时必须带有meal_name字段'
                return output

            if quantity is None:
                output['error'] = '使用' + operation_type + '时必须带有quantity字段'
                return output

            try:
                quantity = int(quantity)
            except:
                output['error'] = 'quantity字段必须是整数数字'
                return output

            try:
                meal_id = self.__list_name.index(meal_name)
            except:
                meal_id = -1
            if meal_id == -1:
                output['error'] = '未找到名为{}的菜品，请确认是否输入错误'.format(meal_name)
                return output

            if meal_id not in self.__order:
                self.__order[meal_id] = 0

            if operation_type == "add":
                self.__order[meal_id] += quantity
            if operation_type == "delete":
                self.__order[meal_id] -= quantity
                if self.__order[meal_id] < 0:
                    self.__order[meal_id] = 0
            if operation_type == "edit":
                self.__order[meal_id] = quantity

            output['success'] = 'modify success'
            output['hint'] = '在告知修改(增删)的情况下，请向客户询问:还需要什么额外的菜品'
            return output

        if operation_type == 'checkout':
            total = 0
            all_select = []
            for id, num in self.__order.items():
                total += self.__list_price[id] * num
                current = {
                    'meal_name' : self.__list_name[id],
                    'quantity' : num
                }
                all_select.append(current)

            #self.order = {}
            output['hint'] = '请将总价告诉给客户，并且确认所点的菜。'
            output['total'] = total
            output['meal_list'] = all_select
            return output

        if operation_type == 'payment':
            output['hint'] = '支付成功'
            return output