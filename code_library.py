from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import sys
import os
import pandas as pd
import math
import importlib.util
import subprocess
from customized_widget import *
import logging
import getpass
import datetime
import ctypes

logging.basicConfig(level=logging.ERROR, filename = "S:/AlanXie/temp/code_library_log/code_library_logging_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".log")
user = getpass.getuser()

# disable winsows console quick edit mode ref: https://stackoverflow.com/questions/13599822/command-prompt-gets-stuck-and-continues-on-enter-key-press
kernel32 = ctypes.windll.kernel32
kernel32.SetConsoleMode(kernel32.GetStdHandle(-10), 128)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        #add keyboard support, details to be modified in newOnkeyPressEvent function
        QMainWindow.keyPressEvent = self.newOnkeyPressEvent

        logging.info(user + " started")

        # read database from csv on shared drive
        self.db = pd.read_csv("S:/AlanXie/code.csv")
        # calculate number of levels
        self.LEVEL = self.db.shape[1] - (len(self.db.columns) - [i for i, word in enumerate(self.db.columns) if word.startswith('Unnamed:')][0])

        self.setWindowTitle("Code Library")

        pagelayout = QVBoxLayout()
        menu_layout = QHBoxLayout()

        main_layout = QHBoxLayout()
        self.stacklayout = QStackedLayout()

        # create des_layout on the right side
        des_label_title = QLabel("Description:")
        self.des_label = QLabel("")
        self.des_label.setWordWrap(True)
        dir_label_title = QLabel("Source file:")
        self.dir_label = QLabel("")
        des_layout = QVBoxLayout()
        des_layout.addWidget(des_label_title, 1)
        des_layout.addWidget(self.des_label, 7)
        des_layout.addWidget(dir_label_title, 1)
        des_layout.addWidget(self.dir_label, 1)
        des_layout.setAlignment(Qt.AlignTop)
        self.des_label.setAlignment(Qt.AlignTop)
        self.dir_label.setAlignment(Qt.AlignTop)

        # add main_layout on the left side
        main_layout.addLayout(self.stacklayout, 5)
        main_layout.addLayout(des_layout, 5)

        # add run_layout at the buttom
        run_layout = QHBoxLayout()
        pagelayout.addLayout(menu_layout)
        pagelayout.addLayout(main_layout)
        pagelayout.addLayout(run_layout)

        self.list = [ListWidget(i) for i in range(self.LEVEL)]
        for i in self.list:
            i.itemClicked.connect(self.listClick)
            i.setSortingEnabled(True)

        # set up the first list
        self.list[0].setup(sorted(set(self.db.iloc[:,0])))
        self.list[0].createMap(self.db.iloc[self.getCurrentSelectedRows()])
        self.list[0].setCurrentRow(0)

        # add back button at the top left corner (in menu)
        self.back_btn = QPushButton("<")
        self.back_btn.setFixedWidth(50)
        self.back_btn.pressed.connect(self.goBack)
        self.back_btn.setEnabled(False)
        self.path_label = QLabel("")
        menu_layout.addWidget(self.back_btn)
        menu_layout.addWidget(self.path_label)

        # add run button at the bottom
        self.run_btn = QPushButton("run")
        self.run_btn.setEnabled(False)
        self.run_btn.index = -1
        self.run_btn.pressed.connect(self.openFile)
        run_layout.addWidget(self.run_btn)

        # # Testing!!!
        # # uncomment the below lines and add test function in test()
        # # remember to also uncomment the test() function below
        # self.test_btn = QPushButton("test")
        # self.test_btn.pressed.connect(self.test)
        # run_layout.addWidget(self.test_btn)
        # # Testing!!!

        # add empty list to list
        for i in self.list:
            self.stacklayout.addWidget(i)

        widget = QWidget()
        widget.setLayout(pagelayout)
        self.setCentralWidget(widget)

    #func for keyboard support
    def newOnkeyPressEvent(self,e):

        if e.key() == Qt.Key_Return or e.key() == Qt.Key_Right:
            self.listClick()
            if self.run_btn.isEnabled():
                self.openFile()
        elif e.key() == Qt.Key_Left:
            if self.stacklayout.currentIndex() > 0:
                self.goBack()

    # called when items in the list is clicked
    def listClick(self):
        logging.info("click list item")
        # get the current level
        idx = self.stacklayout.currentIndex()
        # if the last level is reached
        # if you have more levels, it is recommended to add level columns in the csv
        if idx >= self.LEVEL - 1:
            self.fileClick()
        else:
            selected = self.list[idx].currentItem().text()
            if len(self.db.iloc[self.list[idx].map(selected)]) == 1:
                row = self.db.iloc[self.list[idx].map(selected)].index
                if (not isinstance(self.db.iloc[row, idx+1].values[0], str)) and math.isnan(self.db.iloc[row, idx+1]):
                    self.fileClick()
                    return

            # item clicked is not a file, enter the next level, set up the list for next level
            self.list[idx+1].clear()
            self.list[idx+1].setup(sorted(self.db.iloc[self.list[idx].map(selected)].iloc[:,idx+1].values))
            self.stacklayout.setCurrentIndex(idx+1)
            self.list[idx+1].createMap(self.db.iloc[self.getCurrentSelectedRows(), :])
            self.list[idx+1].setCurrentRow(0)

            self.back_btn.setEnabled(True)
            self.run_btn.setEnabled(False)
            self.run_btn.index = -1

        # update the path in the menu
        self.updatePath(idx)
        logging.info("click list item finished")

    # called when the item in the list clicked is a file
    # update the description on the right and enable the run button at the bottom
    def fileClick(self):
        logging.info("file clicked, ready to run")
        self.run_btn.setEnabled(True)
        idx = self.stacklayout.currentIndex()
        current_item = self.list[idx].currentItem().text()
        self.run_btn.index = self.list[idx].map(current_item)[0]
        try:
            self.dir_label.setText(self.db['directory'].values[self.list[idx].map(current_item)][0])
        except:
            self.dir_label.setText("")
            self.run_btn.setEnabled(False)
            self.run_btn.index = -1
        try:
            self.des_label.setText(self.db['description'].values[self.list[idx].map(current_item)][0])
        except:
            self.des_label.setText("")
        logging.info("file clicked set up finished")

    # called when the back button at the top left corner is clicked, going back to the previous level
    def goBack(self):
        logging.info("go back")
        self.des_label.setText("")
        self.dir_label.setText("")
        idx = self.stacklayout.currentIndex()
        self.list[idx].clear()
        self.stacklayout.setCurrentIndex(idx-1)
        self.run_btn.setEnabled(False)
        self.run_btn.index = -1
        if idx - 1 <= 0:
            self.back_btn.setEnabled(False)
            self.path_label.setText("")
        else:
            self.updatePath(idx-2)
        logging.info("go back finished")

    # update the path in the menu
    def updatePath(self, idx):
        logging.info("update path")
        path_list = []
        for i in range(idx+1):
            path_list.append(self.list[i].currentItem().text())
        self.path_label.setText(" > ".join(path_list))
        logging.info("update finish")

    # called when the run button in clicked, run the file
    def openFile(self):
        logging.info("run file")
        file = self.dir_label.text()
        extension = file.split(".")[-1]
        logging.info("get filename: " + file + " . ready to run")
        # simply open the excel file
        if extension == "csv" or extension == "xlsm" or extension == "xlsx":
            logging.info("open excel")
            os.startfile(file)
            print("open " + file)
            # MACOS: os.system("open " + filename)
            # Windows: os.system("start " + filename)
        # run python script
        elif extension == "py":
            logging.info("run python")
            print("run " + file)
            logging.info("run python message printed")
            # if input is required for the python file
            if isinstance(self.db['require_input'].values[self.run_btn.index], str):
                input = self.db['require_input'].values[self.run_btn.index]

                # if the input required is a form
                if self.db['input_type'].values[self.run_btn.index] == "form":
                    dialog = MultiInputDialog(input.split(";"))
                # if the input required is a list
                elif self.db['input_type'].values[self.run_btn.index] == "list":
                    dialog = ListInputDialog(input)
                elif self.db['input_type'].values[self.run_btn.index] == "file":
                    dialog = FileDialog()

                # if default text is needed
                if self.db['default'].values[self.run_btn.index] == 'Y':

                    try:
                        spec = importlib.util.spec_from_file_location("module", file)
                        foo = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(foo)
                    except Exception as e:
                        msg = QMessageBox()
                        msg.setWindowTitle("ERROR")
                        msg.setIcon(QMessageBox.Critical)
                        msg.setText("Failed to run code:\n" + str(e))
                        msg.exec_()
                        return

                    try:
                        default_list = foo.setup()
                    except:
                        msg = QMessageBox()
                        msg.setWindowTitle("ERROR")
                        msg.setIcon(QMessageBox.Critical)
                        msg.setText("Error on setup")
                        msg.exec_()
                        return

                    dialog.setDefault(default_list)

                # pop up the input dialog and wait for user input
                if dialog.exec():
                    retval = dialog.getInputs()
                    logging.info("get input finished")

                    try:
                        spec = importlib.util.spec_from_file_location("module", file)
                        foo = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(foo)
                    except Exception as e:
                        msg = QMessageBox()
                        msg.setWindowTitle("ERROR")
                        msg.setIcon(QMessageBox.Critical)
                        msg.setText("Failed to run code:\n" + str(e))
                        msg.exec_()
                        return

                    # pop up the confirm dialog, python won't be executed if user chooses no
                    confirm_msg = foo.confirm(retval)
                    logging.info("confirm finished")
                    reply = QMessageBox.question(self, 'Confirm', confirm_msg, QMessageBox.Yes | QMessageBox.No)
                    if reply == QMessageBox.Yes:
                        try:
                            ret_msg = foo.function(retval)

                            # python file executed unsuccessfully
                            if ret_msg is not None and ret_msg["status"] == 0:
                                msg = QMessageBox()
                                msg.setTextInteractionFlags(Qt.TextSelectableByMouse)
                                msg.setText("Error: " + ret_msg["msg"])
                                msg.setWindowTitle("Fail")
                                retval = msg.exec_()
                            # python file executed successfully
                            elif ret_msg is not None and ret_msg["status"] == 1:
                                msg = QMessageBox()
                                msg.setTextInteractionFlags(Qt.TextSelectableByMouse)
                                msg.setText(ret_msg["msg"])
                                msg.setWindowTitle("Successful")
                                retval = msg.exec_()

                                if "type" in ret_msg:
                                    if ret_msg["type"] == "dir":
                                        os.startfile(ret_msg["value"])

                        except Exception as e:
                            # error message if the python fucntion is buggy
                            print("The source function is buggy:")
                            print(e)

            # run python that doesn't need input, python is required on the user's computer
            # but no customization is reuiqred on the python scirpt
            # all printed lines will be shown in a pop up window after execution
            else:
                ret = subprocess.Popen("python \"" + file + "\"", shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                ret_msg = ""
                for line in ret.stdout.readlines():
                    ret_msg += line.decode("utf-8")
                    ret_msg += "\n"
                if ret_msg != "":
                    msg = QMessageBox()
                    msg.setTextInteractionFlags(Qt.TextSelectableByMouse)
                    msg.setText(ret_msg)
                    msg.setWindowTitle("Message")
                    retval = msg.exec_()
                ret.stdout.close()
        logging.info("run file finished")

    # get indices of items in the database which are under items in the currently list
    def getCurrentSelectedRows(self):
        logging.info("get current selected rows")
        idx = self.stacklayout.currentIndex()
        if idx <= 0:
            return range(len(self.db))
        else:
            prev_selected = self.list[idx-1].currentItem().text()
            return self.list[idx-1].map(prev_selected)
        logging.info("get current selected rows finished")

    # # Testing!!!
    # # uncomment this and add your test function here
    # # rememeber to also uncomment the button creation codes above
    # def test(self):
    #     dialog = ListInputDialog("RTL")
    #     if dialog.exec():
    #         print("hahaha")
    # # Testing!!!

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = MainWindow()
    win.resize(600, 400)
    win.show()
    sys.exit(app.exec_())
