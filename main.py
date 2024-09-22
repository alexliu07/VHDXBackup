import datetime
import threading
from concurrent.futures import ThreadPoolExecutor

import ttkbootstrap as ttk
from tkinter import filedialog
from utils import *

work_dir = '{}\\vhdxBackup'.format(os.environ['APPDATA'])
icon_path = '{}\\app.ico'.format(work_dir)
config_path = '{}\\config.json'.format(work_dir)
data_path = '{}\\disks'.format(work_dir)
config = {}
virtual_disks = {}
version = '1.0.0'


class MainWindow:
    def __init__(self):
        self.win = ttk.Window()
        self.win.title('虚拟磁盘管理')
        self.win.iconbitmap(icon_path)
        # 初始化
        while config['backup_path'] == '':
            InitWindow(self.win)
        # 创建任务窗口
        self.task_window = TaskWindow()
        self.win.focus_set()
        # 初始化窗口组件
        self.__init2__()
        # 更新虚拟磁盘列表
        self.update_virtual_disk_table_data()
        self.win.mainloop()

    def __init2__(self):
        self.virtual_disk_frame = ttk.LabelFrame(self.win, text='虚拟磁盘')
        self.list_frame = ttk.Frame(self.virtual_disk_frame, width=600)
        # 创建虚拟磁盘表格显示和操作按钮
        self.virtual_disk_list = self.create_table(self.list_frame)
        # 创建列表旁边的操作按钮
        self.list_btn, self.delete_virtual_disk_btn = self.create_list_control_btn(self.list_frame)
        self.list_frame.pack()
        self.virtual_disk_frame.pack(padx=10, pady=10)
        # 创建备份相关功能
        self.backup_frame = ttk.LabelFrame(self.win, text='备份/还原控制')
        self.backup_list = self.create_backup_list_table(self.backup_frame)
        self.backup_main_btn, self.backup_parent_btn, self.backup_restore_btn, self.backup_delete_btn = self.create_backup_control_btn(
            self.backup_frame)
        self.backup_frame.pack(side=ttk.LEFT, padx=10, pady=10)
        # 创建设置按钮
        self.settings_frame = ttk.LabelFrame(self.win, text='程序控制')
        self.tasks_btn = self.create_settings_btn(self.settings_frame)
        self.settings_frame.pack(padx=10, pady=10)

    def virtual_disk_table_on_change(self, event):
        """
        列表选中之后的处理
        :return:
        """
        item = self.virtual_disk_list.set(self.virtual_disk_list.focus())
        if item:
            id = item['id']
            self.delete_virtual_disk_btn.configure(state=ttk.NORMAL)
            # 判断是否正在进行任务
            if virtual_disks[id].task_state[0] or virtual_disks[id].task_state[2]:
                self.backup_main_btn.configure(state=ttk.DISABLED)
                self.delete_virtual_disk_btn.configure(state=ttk.DISABLED)
            else:
                self.backup_main_btn.configure(state=ttk.NORMAL)
            if virtual_disks[id].hasParent:
                if virtual_disks[id].task_state[1] or virtual_disks[id].task_state[2]:
                    self.backup_parent_btn.configure(state=ttk.DISABLED)
                    self.delete_virtual_disk_btn.configure(state=ttk.DISABLED)
                else:
                    self.backup_parent_btn.configure(state=ttk.NORMAL)
            else:
                self.backup_parent_btn.configure(state=ttk.DISABLED)
        else:
            id = '0'
            self.backup_main_btn.configure(state=ttk.DISABLED)
            self.backup_parent_btn.configure(state=ttk.DISABLED)
            self.delete_virtual_disk_btn.configure(state=ttk.DISABLED)
        self.update_backup_list_table_data(id)

    def create_table(self, root):
        """
        创建虚拟磁盘表格
        :param root: 父控件
        :return: [表格框架, 表格组件]
        """
        columns = ['id', 'path', 'hasParent', 'parentPath']
        table_frame = ttk.Frame(root)
        yscroll = ttk.Scrollbar(table_frame, orient=ttk.VERTICAL)
        table = ttk.Treeview(table_frame, show='headings', columns=columns, yscrollcommand=yscroll.set)
        table.heading('id', text='ID')
        table.heading('path', text='虚拟磁盘路径')
        table.heading('hasParent', text='差分磁盘')
        table.heading('parentPath', text='母盘路径(如果是差分磁盘)')
        table.column('id', width=50, minwidth=50, anchor=ttk.S)
        table.column('path', width=300, minwidth=100)
        table.column('hasParent', width=70, minwidth=70, anchor=ttk.S)
        table.column('parentPath', width=300, minwidth=100)
        yscroll.config(command=table.yview)
        yscroll.pack(side=ttk.RIGHT, fill=ttk.Y)
        table.bind('<<TreeviewSelect>>', self.virtual_disk_table_on_change)
        table.pack(expand=True)
        table_frame.pack(side=ttk.LEFT, pady=10, padx=10)
        return table

    def update_virtual_disk_table_data(self):
        """
        更新虚拟磁盘列表数据
        :return:void
        """
        # 删除原有数据
        obj = self.virtual_disk_list.get_children()
        for i in obj:
            self.virtual_disk_list.delete(i)
        # 添加新数据
        for i, info in enumerate(virtual_disks):
            data = virtual_disks[info]
            if data.hasParent:
                hasParent = '是'
            else:
                hasParent = '否'
            value = [data.id, data.path, hasParent, data.parentPath]
            self.virtual_disk_list.insert('', ttk.END, values=value)

    def create_list_control_btn(self, root):
        """
        创建虚拟磁盘列表右边的操作按钮
        :param root: 父控件
        :return: 按钮框架
        """
        frame = ttk.Frame(root)
        add_btn = ttk.Button(frame, text='添加虚拟磁盘', bootstyle=(ttk.PRIMARY, ttk.OUTLINE),
                             command=self.create_add_window)
        add_btn.pack(padx=10, pady=10)
        del_btn = ttk.Button(frame, text='删除虚拟磁盘', bootstyle=(ttk.DANGER, ttk.OUTLINE),
                             command=self.del_virtual_disk, state=ttk.DISABLED)
        del_btn.pack(padx=10, pady=10)
        frame.pack(pady=50)
        return frame, del_btn

    def create_add_window(self):
        """
        创建新建虚拟磁盘窗口
        :return: void
        """
        AddWindow(self)

    def del_virtual_disk(self):
        """
        删除虚拟磁盘
        :return: void
        """
        curSel = self.virtual_disk_list.set(self.virtual_disk_list.focus())
        # 弹出对话框询问
        dialog = DeleteConfirmWindow(self.win, '虚拟磁盘', virtual_disks[curSel['id']].path)
        value = dialog.show()
        if value == -1:
            return
        virtual_disks.pop(curSel['id'])
        for i in range(len(config['virtual_disks'])):
            if config['virtual_disks'][i] == curSel['id']:
                del config['virtual_disks'][i]
                break
        with open(config_path, 'w+', encoding='utf-8') as f:
            f.write(str(config).replace("'", '"'))
        os.remove('{}\\{}.json'.format(data_path, curSel['id']))
        if value:
            os.remove(curSel['path'])
        self.update_virtual_disk_table_data()

    def create_backup_list_table(self, root):
        """
        创建备份控制页面
        :param root:父控件
        :return:表格控件
        """
        frame = ttk.Frame(root)
        columns = ['id', 'date', 'type', 'size']
        yscroll = ttk.Scrollbar(frame, orient=ttk.VERTICAL)
        table = ttk.Treeview(frame, show='headings', columns=columns, yscrollcommand=yscroll.set)
        table.heading('id', text='ID')
        table.heading('date', text='备份日期')
        table.heading('type', text='类型')
        table.heading('size', text='大小')
        table.column('id', width=50, minwidth=50, anchor=ttk.S)
        table.column('date', width=300, minwidth=150)
        table.column('type', width=50, minwidth=50, anchor=ttk.S)
        table.column('size', width=100, minwidth=50)
        yscroll.config(command=table.yview)
        yscroll.pack(side=ttk.RIGHT, fill=ttk.Y)
        table.bind('<<TreeviewSelect>>', self.backup_table_on_change)
        table.pack(expand=True)
        frame.pack(side=ttk.LEFT, padx=10, pady=10)
        return table

    def backup_table_on_change(self, event):
        """
        备份列表选中之后的处理
        :return:
        """
        item = self.backup_list.set(self.backup_list.focus())
        id = self.virtual_disk_list.set(self.virtual_disk_list.focus())['id']
        if item:
            if virtual_disks[id].task_state[0] or virtual_disks[id].task_state[1]:
                self.backup_restore_btn.configure(state=ttk.DISABLED)
            else:
                self.backup_restore_btn.configure(state=ttk.NORMAL)
            self.backup_delete_btn.configure(state=ttk.NORMAL)
        else:
            self.backup_restore_btn.configure(state=ttk.DISABLED)
            self.backup_delete_btn.configure(state=ttk.DISABLED)

    def update_backup_list_table_data(self, id):
        """
        更新备份列表数据
        :return: void
        """
        # 删除原有数据
        obj = self.backup_list.get_children()
        for i in obj:
            self.backup_list.delete(i)
        if id == '0':
            return
        # 添加新数据
        for i, info in enumerate(virtual_disks[id].backupList):
            data = virtual_disks[id].backupList[info]
            if data['type']:
                type = '母盘'
            else:
                type = '常规'
            value = [data['id'], data['date'], type, data['size']]
            self.backup_list.insert('', ttk.END, values=value)

    def create_backup_control_btn(self, root):
        """
        创建备份控制按钮
        :param root: 父控件
        :return: 备份磁盘按钮,备份母盘按钮,恢复备份按钮
        """
        frame = ttk.Frame(root)
        backup_main = ttk.Button(frame, text='开始备份', bootstyle=(ttk.PRIMARY, ttk.OUTLINE), state=ttk.DISABLED,
                                 command=self.backup_main)
        backup_main.pack(padx=10, pady=10)
        backup_parent = ttk.Button(frame, text='开始备份母盘', bootstyle=(ttk.PRIMARY, ttk.OUTLINE), state=ttk.DISABLED,
                                   command=self.backup_parent)
        backup_parent.pack(padx=10, pady=10)
        restore = ttk.Button(frame, text='恢复选中备份', bootstyle=(ttk.PRIMARY, ttk.OUTLINE), state=ttk.DISABLED,
                             command=self.restore)
        restore.pack(padx=10, pady=10)
        delete = ttk.Button(frame, text='删除选中备份', bootstyle=(ttk.DANGER, ttk.OUTLINE), state=ttk.DISABLED,
                            command=self.del_backup)
        delete.pack(padx=10, pady=10)
        frame.pack(pady=10, padx=10)
        return backup_main, backup_parent, restore, delete

    def del_backup(self):
        """
        删除指定备份文件
        :return:
        """
        disk = self.virtual_disk_list.set(self.virtual_disk_list.focus())
        backup = self.backup_list.set(self.backup_list.focus())
        # 弹出对话框询问
        dialog = DeleteConfirmWindow(self.win, '备份', backup['date'])
        value = dialog.show()
        if value == -1:
            return
        virtual_disks[disk['id']].backupList.pop(backup['id'])
        virtual_disks[disk['id']].save_config()
        if value:
            os.remove('{}\\{}\\{}.vhdx'.format(config['backup_path'], disk['id'], backup['id']))
        self.update_backup_list_table_data(disk['id'])

    def create_settings_btn(self, root):
        """
        创建设置按钮
        :param root: 父控件
        :return: 任务按钮
        """
        frame = ttk.Frame(root)
        settings = ttk.Button(frame, text='软件设置', bootstyle=(ttk.PRIMARY, ttk.OUTLINE),
                              command=self.create_settings_window)
        settings.pack(padx=10, pady=10)
        tasks = ttk.Button(frame, text='当前没有任务正在进行', bootstyle=(ttk.PRIMARY, ttk.OUTLINE),
                           command=self.task_window.show)
        tasks.pack(padx=10, pady=10)
        # automatic function placeholder
        # update function placeholder
        frame.pack(padx=10, pady=10)
        return tasks

    def create_settings_window(self):
        """
        创建设置窗口
        :return: void
        """
        SettingWindow()

    def backup_main(self):
        """
        备份虚拟磁盘
        :return:void
        """
        item = self.virtual_disk_list.set(self.virtual_disk_list.focus())
        id = item['id']
        thread = threading.Thread(target=virtual_disks[id].backup, args=(self.task_window, self))
        thread.start()

    def backup_parent(self):
        """
        备份母盘
        :return: void
        """
        item = self.virtual_disk_list.set(self.virtual_disk_list.focus())
        id = item['id']
        thread = threading.Thread(target=virtual_disks[id].backup_parent, args=(self.task_window, self))
        thread.start()

    def restore(self):
        """
        还原虚拟磁盘
        :return: void
        """
        disk = self.virtual_disk_list.set(self.virtual_disk_list.focus())
        backup = self.backup_list.set(self.backup_list.focus())
        disk_id = disk['id']
        backup_id = backup['id']
        thread = threading.Thread(target=virtual_disks[disk_id].restore, args=(self.task_window, self, backup_id))
        thread.start()

    def update_task_count(self, count):
        """
        更新任务数量
        :return: void
        """
        if count:
            self.tasks_btn.configure(text='当前有 {} 个任务正在进行'.format(count))
        else:
            self.tasks_btn.configure(text='当前没有任务正在进行')


class AddWindow:
    def __init__(self, main_win):
        self.win = ttk.Toplevel()
        self.win.title('添加虚拟磁盘')
        self.win.iconbitmap(icon_path)
        # 初始化窗口组件
        self.__init2__()
        self.mainWin = main_win

    def __init2__(self):
        self.frame = ttk.LabelFrame(self.win, text='添加虚拟磁盘')
        self.parent_check = ttk.IntVar()
        self.path_input = self.create_path_input(self.frame)
        self.create_parent_check(self.frame)
        self.parent_path_input_placeholder, self.parent_path_input_frame, self.parent_path_input = self.create_parent_path_input(
            self.frame)
        self.create_action_button(self.frame)
        self.frame.pack(padx=5, pady=5)

    def create_path_input(self, root):
        """
        创建输入虚拟磁盘路径框
        :param root: 父控件
        :return: 输入框
        """
        frame = ttk.Frame(root)
        hint = ttk.Label(frame, text='虚拟磁盘路径：')
        hint.pack(side=ttk.LEFT, padx=5, pady=10)
        text = ttk.Entry(frame, width=30)
        text.pack(side=ttk.LEFT, padx=5, pady=10)
        sel_btn = ttk.Button(frame, text='选择文件', bootstyle=(ttk.PRIMARY, ttk.OUTLINE),
                             command=self.select_disk_path)
        sel_btn.pack(side=ttk.LEFT, padx=5, pady=10)
        frame.pack(anchor=ttk.W)
        return text

    def select_disk_path(self):
        """
        处理选择磁盘路径
        :return:void
        """
        path = filedialog.askopenfilename(parent=self.win, title='请选择虚拟磁盘',
                                          filetypes=(("VHDX Files", "*.vhdx"),))
        if path:
            self.path_input.delete(0, ttk.END)
            self.path_input.insert(0, path)

    def create_parent_check(self, root):
        """
        创建是否为差分磁盘选择控件
        :param root: 父控件
        :return:void
        """
        frame = ttk.Frame(root)
        hint = ttk.Label(frame, text='差分磁盘：')
        hint.pack(side=ttk.LEFT, padx=5, pady=10)
        check = ttk.Checkbutton(frame, bootstyle=(ttk.ROUND, ttk.TOGGLE), command=self.toggle_parent_check,
                                variable=self.parent_check)
        check.pack(side=ttk.LEFT, padx=5, pady=10)
        frame.pack(anchor=ttk.W)

    def toggle_parent_check(self):
        """
        切换差分磁盘开关
        :return:
        """
        if self.parent_check.get():
            self.parent_path_input_frame.pack(anchor=ttk.W)
        else:
            self.parent_path_input_frame.pack_forget()
            self.parent_path_input_placeholder.configure(height=1)

    def create_parent_path_input(self, root):
        """
        创建输入差分母盘路径框
        :param root: 父控件
        :return: 输入框
        """
        placeholder = ttk.Frame(root)
        frame = ttk.Frame(placeholder)
        hint = ttk.Label(frame, text='母盘路径：')
        hint.pack(side=ttk.LEFT, padx=5, pady=10)
        text = ttk.Entry(frame, width=33)
        text.pack(side=ttk.LEFT, padx=5, pady=10)
        sel_btn = ttk.Button(frame, text='选择文件', bootstyle=(ttk.PRIMARY, ttk.OUTLINE),
                             command=self.select_parent_disk_path)
        sel_btn.pack(side=ttk.LEFT, padx=5, pady=10)
        placeholder.pack()
        return placeholder, frame, text

    def select_parent_disk_path(self):
        """
        处理选择父磁盘路径
        :return:void
        """
        path = filedialog.askopenfilename(parent=self.win, title='请选择母盘', filetypes=(("VHDX Files", "*.vhdx"),))
        if path:
            self.parent_path_input.delete(0, ttk.END)
            self.parent_path_input.insert(0, path)

    def create_action_button(self, root):
        """
        创建保存按钮控件
        :param root: 父控件
        :return: void
        """
        frame = ttk.Frame(root)
        save_btn = ttk.Button(frame, text='保存', command=self.finish_adding, bootstyle=(ttk.SUCCESS, ttk.OUTLINE),
                              width=30)
        save_btn.pack(side=ttk.LEFT, padx=10, pady=10)
        osk_btn = ttk.Button(frame, text='屏幕键盘', command=start_osk, bootstyle=(ttk.PRIMARY, ttk.OUTLINE),
                             width=15)
        osk_btn.pack(side=ttk.LEFT, padx=10, pady=10)
        frame.pack()

    def finish_adding(self):
        """
        保存设置
        :return: void
        """
        path = self.path_input.get()
        hasParent = self.parent_check.get()
        parentPath = self.parent_path_input.get()
        # 判空
        if path == '' or hasParent == 1 and parentPath == '':
            AlartWindow(self.win, '错误', '路径不能为空')
            return
        # 保存
        if not hasParent:
            parentPath = ''
        id = getRandom(5)
        while id in config['virtual_disks']:
            id = getRandom(5)
        data = {'path': path, 'hasParent': hasParent, 'parentPath': parentPath, 'backupList': {}}
        with open('{}\\{}.json'.format(data_path, id), 'w+', encoding='utf-8') as f:
            f.write(str(data).replace("'", '"'))
        virtual_disks[id] = VirtualDisk(id)
        config['virtual_disks'].append(id)
        with open(config_path, 'w+', encoding='utf-8') as f:
            f.write(str(config).replace("'", '"'))
        self.mainWin.update_virtual_disk_table_data()
        self.win.destroy()


class SettingWindow:
    def __init__(self):
        self.win = ttk.Toplevel()
        self.win.title('设置')
        self.win.iconbitmap(icon_path)
        self.check_is_number_func = self.win.register(self.check_is_number)
        # 初始化窗口组件
        self.__init2__()
        # 载入数据
        self.load_current_settings()

    def __init2__(self):
        self.frame = ttk.LabelFrame(self.win, text='软件设置')
        self.backup_path_input = self.create_backup_path_control(self.frame)
        self.chunk_size_input = self.create_chunk_size_set(self.frame)
        self.max_threads_input = self.create_max_threads_set(self.frame)
        self.create_action_button(self.frame)
        self.frame.pack(padx=10, pady=10)

    def load_current_settings(self):
        """
        加载当前设置
        :return:
        """
        self.backup_path_input.insert(0, config['backup_path'])
        self.chunk_size_input.insert(0, config['chunk_size'])
        self.max_threads_input.insert(0, config['max_threads'])

    def create_backup_path_control(self, root):
        """
        创建备份路径设置选项
        :param root: 父控件
        :return: 文本输入框
        """
        frame = ttk.Frame(root)
        hint = ttk.Label(frame, text='备份文件路径：')
        hint.pack(side=ttk.LEFT, padx=5, pady=10)
        text = ttk.Entry(frame, width=30)
        text.pack(side=ttk.LEFT, padx=5, pady=10)
        sel_btn = ttk.Button(frame, text='选择文件夹', bootstyle=(ttk.PRIMARY, ttk.OUTLINE),
                             command=self.select_backup_path)
        sel_btn.pack(side=ttk.LEFT, padx=5, pady=10)
        frame.pack(padx=10, pady=5, anchor=ttk.W)
        return text

    def select_backup_path(self):
        """
        处理选择父磁盘路径
        :return:void
        """
        path = filedialog.askdirectory(parent=self.win, title='请选择备份文件夹')
        if path:
            self.backup_path_input.delete(0, ttk.END)
            self.backup_path_input.insert(0, path)

    def create_chunk_size_set(self, root):
        """
        创建区块大小设置选项
        :return:void
        """
        frame = ttk.Frame(root)
        hint = ttk.Label(frame, text='复制文件时缓存区块大小(字节)：')
        hint.pack(side=ttk.LEFT, padx=5, pady=10)
        text = ttk.Entry(frame, width=10, validate='key', validatecommand=(self.check_is_number_func, '%P'))
        text.pack(side=ttk.LEFT, padx=5, pady=10)
        frame.pack(padx=10, pady=5, anchor=ttk.W)
        return text

    def check_is_number(self, content):
        """
        验证字符串是否为数字
        :param content:字符串
        :return:void
        """
        if content == '':
            return True
        return content.isdigit()

    def create_max_threads_set(self, root):
        """
        创建最大线程数设置选项
        :return: void
        """
        frame = ttk.Frame(root)
        hint = ttk.Label(frame, text='复制文件时最大线程数：')
        hint.pack(side=ttk.LEFT, padx=5, pady=10)
        text = ttk.Entry(frame, width=5, validate='key', validatecommand=(self.check_is_number_func, '%P'))
        text.pack(side=ttk.LEFT, padx=5, pady=10)
        frame.pack(padx=10, pady=5, anchor=ttk.W)
        return text

    def create_action_button(self, root):
        """
        创建保存按钮控件
        :param root: 父控件
        :return: void
        """
        frame = ttk.Frame(root)
        save_btn = ttk.Button(frame, text='保存', command=self.finish_setting, bootstyle=(ttk.SUCCESS, ttk.OUTLINE),
                              width=30)
        save_btn.pack(side=ttk.LEFT, padx=10, pady=10)
        osk_btn = ttk.Button(frame, text='屏幕键盘', command=start_osk, bootstyle=(ttk.PRIMARY, ttk.OUTLINE),
                             width=15)
        osk_btn.pack(side=ttk.LEFT, padx=10, pady=10)
        frame.pack()

    def finish_setting(self):
        """
        保存设置
        :return: void
        """
        if not self.backup_path_input.get() or not self.chunk_size_input.get() or not self.max_threads_input.get():
            AlartWindow(self.win, '错误', '设置不能为空')
            return
        # 保存
        config['backup_path'] = self.backup_path_input.get()
        config['chunk_size'] = self.chunk_size_input.get()
        config['max_threads'] = self.max_threads_input.get()
        with open(config_path, 'w+', encoding='utf-8') as f:
            f.write(str(config).replace("'", '"'))
        self.win.destroy()


class InitWindow(SettingWindow, ttk.Frame):
    def __init__(self,master):
        ttk.Frame.__init__(self,master)
        self.win = ttk.Toplevel()
        self.win.title('初始化')
        self.win.iconbitmap(icon_path)
        self.check_is_number_func = self.win.register(self.check_is_number)
        self.__init2__()
        self.load_current_settings()
        self.win.transient(master)
        self.win.grab_set()
        self.wait_window(self.win)

    def __init2__(self):
        self.frame = ttk.LabelFrame(self.win, text='初始化')
        self.backup_path_input = self.create_backup_path_control(self.frame)
        self.chunk_size_input = self.create_chunk_size_set(self.frame)
        self.max_threads_input = self.create_max_threads_set(self.frame)
        self.create_action_button(self.frame)
        self.frame.pack(padx=10, pady=10)

class TaskWindow:
    def __init__(self):
        self.win = ttk.Toplevel()
        self.win.title('任务列表')
        self.win.iconbitmap(icon_path)
        self.win.protocol("WM_DELETE_WINDOW", self.hide)
        self.hide()
        self.task_count = 0
        # 加载布局
        self.__init2__()

    def __init2__(self):
        self.task_frame, self.empty_text = self.create_task_list(self.win)

    def show(self):
        """
        显示窗口
        :return: void
        """
        self.win.deiconify()

    def hide(self):
        """
        隐藏窗口
        :return: void
        """
        self.win.withdraw()

    def create_task_list(self, root):
        frame = ttk.LabelFrame(root, text='任务列表')
        hint = ttk.Label(frame, text='当前没有任务正在进行')
        hint.pack(padx=10, pady=10)
        frame.pack(padx=10, pady=10)
        return frame, hint

    def update_hint(self):
        """
        更新无任务标签
        :return:
        """
        if self.task_count == 0:
            self.empty_text.pack(padx=10, pady=10)
        else:
            self.empty_text.pack_forget()


class AlartWindow(ttk.Frame):
    def __init__(self, master, title, content):
        ttk.Frame.__init__(self, master)
        self.master = master
        self.title = title
        self.content = content
        self.win = ttk.Toplevel()
        self.win.title(self.title)
        self.win.iconbitmap(icon_path)
        self.__init2__()

    def __init2__(self):
        self.text = ttk.Label(self.win, text=self.content)
        self.text.pack(padx=10, pady=10)
        self.confirm_btn = ttk.Button(self.win, text='完成', bootstyle=(ttk.PRIMARY, ttk.OUTLINE), width=25,
                                      command=self.win.destroy)
        self.confirm_btn.pack(padx=10, pady=10)
        self.win.transient(self.master)
        self.win.grab_set()

    def show(self):
        """
        展示窗口
        :return: void
        """
        self.wait_window(self.win)


class DeleteConfirmWindow(ttk.Frame):
    def __init__(self, master, type, name):
        ttk.Frame.__init__(self, master)
        self.master = master
        self.type = type
        self.name = name
        self.delete_file = ttk.IntVar()
        self.value = -1
        self.win = ttk.Toplevel()
        self.win.title('删除{}'.format(self.type))
        self.win.iconbitmap(icon_path)
        self.__init2__()

    def __init2__(self):
        self.hint = ttk.Label(self.win, text='确定要删除{} {} 吗？'.format(self.type, self.name))
        self.hint.pack(padx=10, pady=10)
        self.checkbox = ttk.Checkbutton(self.win, variable=self.delete_file, text='同时删除本地文件')
        self.checkbox.pack(padx=10, pady=10)
        self.ok_btn = ttk.Button(self.win, text='确定', bootstyle=(ttk.SUCCESS, ttk.OUTLINE), width=25, command=self.ok)
        self.ok_btn.pack(side=ttk.LEFT, padx=10, pady=10)
        self.cancel_btn = ttk.Button(self.win, text='取消', bootstyle=(ttk.PRIMARY, ttk.OUTLINE), width=25,
                                     command=self.win.destroy)
        self.cancel_btn.pack(padx=10, pady=10)
        self.win.transient(self.master)
        self.win.grab_set()

    def show(self):
        """
        展示窗口
        :return: -1 取消 0 不删除本地文件 1 删除本地文件
        """
        self.wait_window(self.win)
        return self.value

    def ok(self):
        """
        按下确定按钮
        :return: void
        """
        self.value = self.delete_file.get()
        self.win.destroy()


class BackupRestoreConfirmWindow(ttk.Frame):
    def __init__(self, master, backup_name, disk_path):
        ttk.Frame.__init__(self, master)
        self.master = master
        self.backup_name = backup_name
        self.disk_path = disk_path
        self.value = 0
        self.win = ttk.Toplevel()
        self.win.title('恢复备份')
        self.win.iconbitmap(icon_path)
        self.__init2__()

    def __init2__(self):
        self.hint = ttk.Label(self.win,
                              text='确定要将备份 {} \n恢复到 {} 吗？\n这会覆盖当前的数据'.format(self.backup_name,
                                                                                                self.disk_path))
        self.hint.pack(padx=10, pady=10)
        self.ok_btn = ttk.Button(self.win, text='确定', bootstyle=(ttk.SUCCESS, ttk.OUTLINE), width=25, command=self.ok)
        self.ok_btn.pack(side=ttk.LEFT, padx=10, pady=10)
        self.cancel_btn = ttk.Button(self.win, text='取消', bootstyle=(ttk.PRIMARY, ttk.OUTLINE), width=25,
                                     command=self.win.destroy)
        self.cancel_btn.pack(padx=10, pady=10)
        self.win.transient(self.master)
        self.win.grab_set()

    def show(self):
        """
        展示窗口
        :return: -1 取消 0 不删除本地文件 1 删除本地文件
        """
        self.wait_window(self.win)
        return self.value

    def ok(self):
        """
        按下确定按钮
        :return: void
        """
        self.value = 1
        self.win.destroy()


class Task:
    def __init__(self, type, source, destination, task_window, main_window):
        if type == 0:
            self.type = '备份虚拟磁盘'
        elif type == 1:
            self.type = '备份母盘'
        else:
            self.type = '还原虚拟磁盘'
        self.source = source
        self.destination = destination
        self.task_window = task_window
        self.main_window = main_window
        self.chunk_size = config['chunk_size']
        self.max_threads = config['max_threads']
        self.total_size = 0
        self.current = 0
        self.stop = False
        self.lock = threading.Lock()
        # 创建任务列表组件
        self.frame, self.percentage_text, self.progress_bar, self.progress_text, self.cancel_btn = self.task_info(
            self.task_window.task_frame)
        # 启动任务
        self.start_task()

    def md5sum(self, path):
        """
        计算文件MD5
        :param path: 文件路径
        :return:文件的MD5值
        """
        f = open(path, 'rb')
        m = hashlib.md5()
        # 大文件处理
        while True:
            if self.stop:
                break
            d = f.read(8096)
            if not d:
                break
            m.update(d)
        if self.stop:
            return
        ret = m.hexdigest()
        f.close()
        return ret

    def update_info(self):
        """
        更新进度信息
        :return: void
        """
        self.percentage_text.configure(text='%.2f' % (self.current / self.total_size * 100) + ' %')
        self.progress_bar.configure(value=round(self.current / self.total_size * 100))

    def task_info(self, root):
        """
        任务列表组件
        :param root: 父控件
        :return: 框架,进度条文本,进度条
        """
        frame = ttk.Frame(root)
        text = ttk.Label(frame, text='{}\n{}'.format(self.type, self.source))
        text.pack(padx=10, pady=5)
        progress_text = ttk.Label(frame)
        progress_text.pack(padx=10, pady=5)
        progress_bar = ttk.Progressbar(frame, bootstyle=ttk.INFO, length=100)
        progress_bar.pack(side=ttk.LEFT, padx=10, pady=5)
        percentage_text = ttk.Label(frame, text='0.00%')
        percentage_text.pack(side=ttk.LEFT, padx=10, pady=5)
        cancel_btn = ttk.Button(frame, text='取消', bootstyle=(ttk.PRIMARY, ttk.OUTLINE), command=self.cancel_task)
        cancel_btn.pack(padx=10, pady=5)
        frame.pack(padx=10, pady=5)
        return frame, percentage_text, progress_bar, progress_text, cancel_btn

    def copy_chunk(self, source_file, destination_file, start, size):
        """
        复制单个区块
        :param source_file: 源文件
        :param destination_file: 目标文件
        :param start: 起始位置
        :param size: 区块大小
        :return:
        """
        if self.stop:
            return
        with open(source_file, 'rb', buffering=self.chunk_size) as a, open(destination_file, 'rb+',
                                                                           buffering=self.chunk_size) as b:
            a.seek(start)
            chunk = a.read(size)
            b.seek(start)
            b.write(chunk)
            b.flush()
        self.lock.acquire()
        self.current += size
        self.update_info()
        self.lock.release()

    def start_task(self):
        # 检测文件是否存在
        if not os.path.exists(self.source):
            AlartWindow(self.main_window.win, '错误', '源文件不存在').show()
            return
        # 创建线程池
        thread_pool = ThreadPoolExecutor(max_workers=self.max_threads)
        # 计算文件大小
        total_size = os.path.getsize(self.source) - 1
        self.total_size = total_size + 1
        # 计算文件MD5值
        self.progress_text.config(text='正在计算源文件MD5...')
        source_md5 = self.md5sum(self.source)
        if self.stop:
            thread_pool.shutdown()
            self.finish_task()
            return
        # 创建空文件
        self.progress_text.config(text='正在复制文件...')
        file = open(self.destination, 'w+')
        file.close()
        # 分块拷贝
        progress = -1
        while progress < total_size:
            if self.stop:
                break
            start = progress + 1
            if start + self.chunk_size > total_size:
                size = total_size - start + 1
            else:
                size = self.chunk_size
            thread_pool.submit(self.copy_chunk, self.source, self.destination, start, size)
            progress += size
        thread_pool.shutdown()
        if self.stop:
            os.remove(self.destination)
            self.finish_task()
            return
        # 验证MD5
        self.progress_text.config(text='正在验证文件MD5...')
        destination_md5 = self.md5sum(self.destination)
        if not source_md5 == destination_md5:
            AlartWindow(self.task_window.win, '错误', '文件复制时出现问题').show()
        # 完成任务
        self.finish_task()

    def finish_task(self):
        """
        完成任务
        :return: void
        """
        self.frame.pack_forget()

    def cancel_task(self):
        """
        取消任务
        :return:
        """
        self.stop = True
        self.cancel_btn.configure(state=ttk.DISABLED)


class VirtualDisk:
    def __init__(self, id):
        self.id = id
        self.config_path = '{}\\{}.json'.format(data_path, self.id)
        self.task_state = [False, False, False]
        # 读取磁盘配置文件
        self.__init2__()

    def __init2__(self):
        with open(self.config_path, 'r', encoding='utf-8') as f:
            info = eval(f.read())
        self.path = info['path']
        self.hasParent = info['hasParent']
        self.parentPath = info['parentPath']
        self.backupList = info['backupList']

    def save_config(self):
        """
        保存配置文件
        :return: void
        """
        info = {'path': self.path, 'hasParent': self.hasParent, 'parentPath': self.parentPath,
                'backupList': self.backupList}
        with open(self.config_path, 'w+', encoding='utf-8') as f:
            f.write(str(info).replace("'", '"'))

    def backup(self, task_window, main_window):
        """
        备份主虚拟磁盘
        :param task_window: 任务窗口
        :param main_window: 主窗口
        :return:void
        """
        # 备份还原按钮禁用
        main_window.backup_main_btn.configure(state=ttk.DISABLED)
        main_window.backup_restore_btn.configure(state=ttk.DISABLED)
        # 设置备份状态
        self.task_state[0] = True
        # 新建备份文件夹
        if not os.path.exists('{}\\{}'.format(config['backup_path'], self.id)):
            os.mkdir('{}\\{}'.format(config['backup_path'], self.id))
        # 随机生成备份ID
        backup_id = getRandom(5)
        while backup_id in self.backupList:
            backup_id = getRandom(5)
        target_path = '{}\\{}\\{}.vhdx'.format(config['backup_path'], self.id, backup_id)
        # 任务数量+1并更新任务显示
        task_window.task_count += 1
        task_window.update_hint()
        main_window.update_task_count(task_window.task_count)
        # 创建并执行任务
        task = Task(0, self.path, target_path, task_window, main_window)
        # 任务取消
        if task.stop:
            self.task_state[0] = False
            main_window.backup_main_btn.configure(state=ttk.NORMAL)
            self.finish_backup_task(task_window, main_window)
            return
        # 任务完成后保存记录
        md5 = md5sum(target_path)
        size = hum_convert(os.path.getsize(target_path))
        self.backupList[backup_id] = {'id': backup_id, 'date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                      'type': 0, 'size': size, 'md5': md5}
        self.save_config()
        main_window.update_backup_list_table_data(self.id)
        # 设置备份状态
        self.task_state[0] = False
        # 完成任务
        main_window.backup_main_btn.configure(state=ttk.NORMAL)
        self.finish_backup_task(task_window, main_window)

    def backup_parent(self, task_window, main_window):
        """
        备份母盘
        :param task_window: 任务窗口
        :param main_window: 主窗口
        :return:void
        """
        # 备份还原按钮禁用
        main_window.backup_parent_btn.configure(state=ttk.DISABLED)
        main_window.backup_restore_btn.configure(state=ttk.DISABLED)
        # 设置备份状态
        self.task_state[1] = True
        # 新建备份文件夹
        if not os.path.exists('{}\\{}'.format(config['backup_path'], self.id)):
            os.mkdir('{}\\{}'.format(config['backup_path'], self.id))
        # 随机生成备份ID
        backup_id = getRandom(5)
        while backup_id in self.backupList:
            backup_id = getRandom(5)
        target_path = '{}\\{}\\{}.vhdx'.format(config['backup_path'], self.id, backup_id)
        # 任务数量+1并更新任务显示
        task_window.task_count += 1
        task_window.update_hint()
        main_window.update_task_count(task_window.task_count)
        # 创建并执行任务
        task = Task(1, self.parentPath, target_path, task_window, main_window)
        # 任务取消
        if task.stop:
            self.task_state[1] = False
            main_window.backup_parent_btn.configure(state=ttk.NORMAL)
            self.finish_backup_task(task_window, main_window)
            return
        # 任务完成后保存记录
        md5 = md5sum(target_path)
        size = hum_convert(os.path.getsize(target_path))
        self.backupList[backup_id] = {'id': backup_id, 'date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                      'type': 1, 'size': size, 'md5': md5}
        self.save_config()
        main_window.update_backup_list_table_data(self.id)
        # 设置备份状态
        self.task_state[1] = False
        # 完成任务
        main_window.backup_parent_btn.configure(state=ttk.NORMAL)
        self.finish_backup_task(task_window, main_window)

    def finish_backup_task(self, task_window, main_window):
        """
        完成任务
        :param task_window: 任务窗口
        :param main_window: 主窗口
        :return:
        """
        task_window.task_count -= 1
        task_window.update_hint()
        main_window.update_task_count(task_window.task_count)
        main_window.backup_restore_btn.configure(state=ttk.NORMAL)

    def restore(self, task_window, main_window, backup_id):
        # 确认恢复
        dialog = BackupRestoreConfirmWindow(main_window.win, self.backupList[backup_id]['date'], self.path)
        value = dialog.show()
        if not value:
            return
        # 备份按钮禁用
        main_window.backup_main_btn.configure(state=ttk.DISABLED)
        main_window.backup_parent_btn.configure(state=ttk.DISABLED)
        main_window.backup_restore_btn.configure(state=ttk.DISABLED)
        # 设置备份状态
        self.task_state[2] = True
        source_path = '{}\\{}\\{}.vhdx'.format(config['backup_path'], self.id, backup_id)
        # 任务数量+1并更新任务显示
        task_window.task_count += 1
        task_window.update_hint()
        main_window.update_task_count(task_window.task_count)
        # 创建并执行任务
        target_path = self.parentPath if self.backupList[backup_id]['type'] else self.path
        task = Task(2, source_path, target_path, task_window, main_window)
        # 任务取消
        if task.stop:
            self.finish_restore_task(task_window, main_window)
            return
        # 完成任务
        self.finish_restore_task(task_window, main_window)

    def finish_restore_task(self, task_window, main_window):
        """
        完成还原任务
        :return: void
        """
        self.task_state[2] = False
        main_window.backup_main_btn.configure(state=ttk.NORMAL)
        if self.hasParent:
            main_window.backup_parent_btn.configure(state=ttk.NORMAL)
        self.finish_backup_task(task_window, main_window)


if __name__ == '__main__':
    # 初始化
    if not os.path.exists(work_dir):
        os.mkdir(work_dir)
    if not os.path.exists(data_path):
        os.mkdir(data_path)
    if not os.path.exists(config_path):
        default_config = {
            'backup_path': '',
            'virtual_disks': [],
            'chunk_size': 1024 * 1024 * 32,
            'max_threads': 10
        }
        with open(config_path, 'w+', encoding='utf-8') as f:
            f.write(str(default_config).replace("'", '"'))
    # 解压图标
    if not os.path.exists(icon_path):
        extract_app_icon(icon_path)
    # 读取配置
    with open(config_path, 'r', encoding='utf-8') as f:
        config = eval(f.read())
    for i in config['virtual_disks']:
        virtual_disks[i] = VirtualDisk(i)
    win = MainWindow()
