import tkinter as tk
from tkinter import font as tkFont
import threading


def create_window(get_response):
    # 这个函数会在用户按下发送按钮或者回车键时被调用
    def on_send_button_click(event=None):
        user_input = user_input_entry.get()
        if user_input:
            update_chat_history("你: " + user_input + "\n")

            # 清空输入框并禁用发送按钮
            user_input_entry.delete(0, tk.END)
            send_button.config(state=tk.DISABLED)

            # 开启一个新线程处理机器人的响应
            threading.Thread(target=get_bot_response, args=(user_input,)).start()

    # 更新聊天历史文本框的内容
    def update_chat_history(message):
        chat_history_text.config(state=tk.NORMAL)
        chat_history_text.insert(tk.END, message)
        chat_history_text.config(state=tk.DISABLED)
        chat_history_text.see(tk.END)  # 自动滚动到文本框的底部

    # 在单独的线程中获取机器人的响应并更新UI
    def get_bot_response(user_input):
        response = get_response(user_input)
        # 通过使用tkinter的after方法来在主线程中更新UI
        chat_history_text.after(0, update_chat_history, "机器人: " + response + "\n")
        # 重新激活发送按钮
        send_button.config(state=tk.NORMAL)

    # 尝试设置应用程序为高DPI感知以解决模糊问题（仅在Windows系统有效）
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception as e:
        print(e)

    # 创建主窗口
    root = tk.Tk()
    root.title("聊天机器人")

    # 设置聊天窗口和输入窗口的字体样式
    chat_font = tkFont.Font(family='SimHei', size=18, weight='normal')  # 这里设置字体和大小
    input_font = tkFont.Font(family='SimHei', size=18, weight='normal')  # 这里设置字体和大小

    # 创建一个文本框显示聊天历史，并应用字体
    chat_history_text = tk.Text(root, state=tk.DISABLED, font=chat_font)
    chat_history_text.pack(padx=10, pady=10, expand=True, fill=tk.BOTH)

    # 创建一个输入框，并应用字体
    user_input_entry = tk.Entry(root, font=input_font)
    user_input_entry.pack(padx=10, pady=10, fill=tk.X)
    user_input_entry.bind("<Return>", on_send_button_click)

    # 创建一个发送按钮
    send_button = tk.Button(root, text="发送", command=on_send_button_click)
    send_button.pack(padx=10, pady=10)

    # 让窗口执行
    root.mainloop()