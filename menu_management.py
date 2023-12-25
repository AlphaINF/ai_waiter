
from llm.gpt import embedding, chat
import os
from tqdm import tqdm
import pickle
import numpy as np
import pandas as pd
import hashlib
import pickle
import json

class Waiter:

    # 计算数据列表对应的sha256
    def __calculate_sha256(self):
        my_list = self.__list_id + self.__list_type + self.__list_name + self.__list_price + self.__list_notes
        serialized_list = pickle.dumps(my_list)
        # 计算这个字节流的SHA256哈希值
        hash_object = hashlib.sha256(serialized_list)
        hash_hex = hash_object.hexdigest()
        return hash_hex

    # sha256校验器，用于给menu.xlsx的embedding缓存进行校验
    # 如果无法通过sha256校验，则会自动生成新的embedding缓存
    def __check_file_sha256(self, xlsx_file_path):
        # 计算xlsx文件的哈希值
        xlsx_file_sha256 = self.__calculate_sha256()

        # 生成哈希文件的完整路径
        hash_file_path = os.path.splitext(xlsx_file_path)[0] + '.sha256'

        # 检查哈希值文件是否存在
        if not os.path.isfile(hash_file_path):
            print(f"Hash file {hash_file_path} does not exist.")
            return False

        # 读取哈希值文件
        with open(hash_file_path, 'r') as file:
            stored_hash = file.read().strip()

        # 比较哈希值
        return xlsx_file_sha256 == stored_hash

    # 初始化
    # 如果菜品没有建立索引，则会自动建立
    def __init__(self, filename):
        df = pd.read_excel(filename)

        self.__filename = filename
        self.__list_id = df['编号'].tolist()
        self.__list_type = df['类别'].tolist()
        self.__list_name = df['名称'].tolist()
        self.__list_price = df['价格'].tolist()
        self.__list_notes = df['备注'].tolist()
        self.__list_stock = df['库存'].tolist()

        self.__order = {}
        self.__len = len(self.__list_id)

        # 对embedding缓存进行sha256校验
        embedding_cache_filename = filename.replace('.xlsx', '.embe')
        if os.path.exists(embedding_cache_filename) and self.__check_file_sha256(filename):
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

            sha256_filename = filename.replace('.xlsx','.sha256')
            with open(sha256_filename, 'w') as f:
                f.write(self.__calculate_sha256())


    # 菜品的粗筛系统
    # 如果type为"餐桌用品", 则会只保留餐桌用品部分的信息
    def __embedding_search(self, instruction, type):
        target_embedding = np.array(embedding(instruction)).astype(np.float32)
        cos_sims = self.__embedding_list.dot(target_embedding).tolist()

        permutation = [i for i in range(self.__len) if (type != '餐桌用品' or self.__list_type[i] == type)]
        permutation = sorted(permutation, key = lambda x:cos_sims[x], reverse=True)
        name_list = [(i, cos_sims[i]) for i in permutation]

        return name_list

    #基于向量检索实现粗筛，随后由该模块进行精筛，选出符合条件的菜，返回其ID
    def __accurate_search(self, instruction, type='菜'):
        prompt_template = '''现在有一个{0}，它的特征如下:
```
{1}
```

现在用户表示，它需要的{0}的特征为:
```
{2}
```

请你判断该{0}是否符合用户的要求。
请注意：特征可能是别名，请注意处理别名。
如果符合请你输出True，否则输出False'''
        name_list = self.__embedding_search(instruction, type)

        import concurrent.futures

        # 定义一个线程工作函数
        def thread_work(i):
            id = name_list[i][0]
            if type == '菜':
                meal_trait_str = '类别:{}\n名称:{}\n价格:{}\n备注:{}'.format(self.__list_type[id], self.__list_name[id], self.__list_price[id], self.__list_notes[id])
            else:
                # 对于查询物品的情况，采用另外的输入内容
                meal_trait_str = '名称:{}\n价格:{}\n备注:{}'.format(self.__list_name[id], self.__list_price[id], self.__list_notes[id])
                meal_trait_str = meal_trait_str.replace('本店不提供', '')
            prompt = prompt_template.format(type, meal_trait_str, instruction)
            #print(prompt)
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
    def __get_item_by_id(self, meal_list):
        output = []
        for id in meal_list:
            meal = {
                'type': self.__list_type[id],
                'name': self.__list_name[id],
                'price': self.__list_price[id]
            }
            if self.__list_notes:
                meal['appendix'] = self.__list_notes[id]
            if self.__list_stock[id] == 0:
                meal['stock'] = '无库存'

            output.append(meal)

        return output

    def __output_tableware_prompt_by_length(self, length):
        if length == 0:
            return '未找到顾客所需的物品，请你直接向顾客说:"没有该物品，但你非常需要的话我可以试着问下店长"'
        if length == 1:
            return '已找到唯一的物品，请你结合提示信息回复顾客，如果客户明确表示需要这款产品，请直接调用点菜插件将其加入订单'
        if length > 1:
            return '找到多种客户可能需要的物品，请你向客户确认需要哪一种\n注意：如果接下来客户讲述的时候，无法决定具体是哪个物品，请你向客户主动询问!!!'

    def get_tableware(self, name):
        output = {}
        tableware_list = self.__accurate_search(name, '餐桌用品')
        output['hint'] = self.__output_tableware_prompt_by_length(len(tableware_list))
        output['items'] = self.__get_item_by_id(tableware_list)

        # 如果没有找到所需的物品，则会向客户表示没有物品，并询问是否需要问一下店长，但下一轮的对话中不会启用任何的函数调用
        if len(tableware_list) == 0:
            output['mask'] = True

        # 如果物品要收费，则要跟客户进行确认
        for item in output['items']:
            if item['price'] != 0:
                output['hint'] = '注意：物品需要收费，加入前请向客户确认!!!!!!\n注意：物品需要收费，加入前请向客户确认!!!!!!'
                break

        return output

    def __output_meal_prompt_by_length(self, length):
        if length == 0:
            return '未找到符合条件的菜品，请向客户说明'
        if length == 1:
            return '已找到唯一的菜品，如果客户明确表示需要这款产品，请直接调用点菜插件将其加入订单，否则请向客户介绍本餐厅存在该菜品'
        if length > 1:
            return '找到多种客户可能需要的菜品，请你分析现有信息是否足以确定是哪一种？如果可以则根据客户要求直接加入系统或向客户介绍。如无法决定具体是哪个菜品，请你向客户主动询问!!!'

    def get_meal(self, meal_description):
        output = {}
        meal_id_list = self.__accurate_search(meal_description)
        output['hint'] = self.__output_meal_prompt_by_length(len(meal_id_list))
        output['meals'] = self.__get_item_by_id(meal_id_list)
        return output

    def call_supervisor(self, context):
        print('求助:', context)
        response = input('店长:')
        return {
            "response": response,
            "mask": True
        }

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

            previous_num_order = self.__order[meal_id]
            if operation_type == "add":
                self.__order[meal_id] += quantity
            if operation_type == "delete":
                self.__order[meal_id] -= quantity
                if self.__order[meal_id] < 0:
                    self.__order[meal_id] = 0
            if operation_type == "edit":
                self.__order[meal_id] = quantity

            if self.__order[meal_id] > self.__list_stock[meal_id]:
                output['error'] = '超出库存限制，用户需要{}，实际库存为{}'.format(self.__order[meal_id], self.__list_stock[meal_id])
                self.__order[meal_id] = previous_num_order
                output['mask'] = True
                return output

            output['success'] = 'modify success'
            output['hint'] = '在告知修改(增删)的情况下，请向客户询问:还需要什么额外的菜品'
            return output

        if operation_type == 'checkout':
            total = 0
            all_select = []
            # 增加了库存规则控制
            for id, num in self.__order.items():
                if self.__list_stock[id] < num:
                    output['error'] += '{}超出库存限制\n'.format(self.__list_name[id])
                total += self.__list_price[id] * num
                current = {
                    'meal_name' : self.__list_name[id],
                    'quantity' : num
                }
                all_select.append(current)

            if 'error' in output:
                output['mask'] = True
                return output
            #self.order = {}
            output['hint'] = '请将总价告诉给客户，并且确认所点的菜。'
            output['total'] = total
            output['meal_list'] = all_select
            return output

        if operation_type == 'payment':
            # 检查库存
            for id, num in self.__order.items():
                if self.__list_stock[id] < num:
                    output['error'] += '{}超出库存限制\n'.format(self.__list_name[id])

            if 'error' in output:
                output['mask'] = True
                return output

            for id, num in self.__order.items():
                self.__list_stock[id] -= num

            # 根据列表创建一个字典，这将成为DataFrame的基础
            data = {
                '编号': self.__list_id,
                '类别': self.__list_type,
                '名称': self.__list_name,
                '价格': self.__list_price,
                '备注': self.__list_notes,
                '库存': self.__list_stock
            }
            # 根据字典创建DataFrame
            df = pd.DataFrame(data)
            # 将DataFrame写回excel文件，如果要保留原始Excel文件的格式和公式，可能需要更复杂的处理
            df.to_excel(self.__filename, index=False)


            output['hint'] = '支付成功'
            return output