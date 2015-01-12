from PyQt4 import QtCore, QtGui

import atexit
import sys

from pb_manager import DB, TDB, tsh_paste, pb_paste, pb_update, \
                       pb_delete, pb_db_write, tsh_db_write

class PBManager(QtGui.QMainWindow):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.tshtv = UrlDropPlace(self)
		self.tshtv.setModel(DBTableModel(TDB))
		self.tshtv.setDragDropMode(QtGui.QAbstractItemView.DropOnly)
		self.tshtv.setAcceptDrops(True)

		self.ptpbtv = UrlDropPlace(self)
		self.ptpbtv.setModel(DBTableModel(DB))
		self.ptpbtv.setDragDropMode(QtGui.QAbstractItemView.DropOnly)
		self.ptpbtv.setAcceptDrops(True)

		self.ptpbtv.dropped.connect(self.ptpb_paste)
		self.tshtv.dropped.connect(self.tsh_paste)

		tabview = QtGui.QTabWidget(self)
		tabview.addTab(self.ptpbtv, "ptpb.pw instance")
		tabview.addTab(self.tshtv, "transfer.sh instance")
		self.setCentralWidget(tabview)

	def ptpb_paste(self, urls):
		attop=QtCore.QModelIndex()
		lastrow=self.ptpbtv.model().rowCount(attop)+1
		lastnewrow=len(urls)+lastrow
		self.ptpbtv.model().beginInsertRows(attop, lastrow, lastnewrow)
		for url in urls:
			if url.toLocalFile() == "":
				pb_paste(url.toString(), alias=True)
			else:
				pb_paste(url.toLocalFile())
		self.ptpbtv.model().endInsertRows()
		#print(urls)

	def tsh_paste(self, urls):
		attop=QtCore.QModelIndex()
		lastrow=self.tshtv.model().rowCount(attop)+1
		lastnewrow=len(urls)+lastrow
		self.tshtv.model().beginInsertRows(attop, lastrow, lastnewrow)
		batch_list=[]
		for url in urls:
			if url.toLocalFile() != "":
				batch_list.append(url.toLocalFile())
		tsh_paste(*batch_list, same_link=True)
		self.tshtv.model().endInsertRows()

#http://stackoverflow.com/questions/4151637/pyqt4-drag-and-drop-files-into-qlistwidget
class UrlDropPlace(QtGui.QTreeView):
	dropped = QtCore.pyqtSignal(list)
	def dragEnterEvent(self, event):
		if event.mimeData().hasUrls():
			event.accept()
		else:
			event.ignore()
	def dragMoveEvent(self, event):
		if event.mimeData().hasUrls():
			event.setDropAction(QtCore.Qt.CopyAction)
			event.accept()
		else:
			event.ignore()
	def dropEvent(self, event):
		if event.mimeData().hasUrls():
			event.setDropAction(QtCore.Qt.CopyAction)
			self.dropped.emit(event.mimeData().urls())
			event.accept()
		else:
			event.ignore()

class DBTableModel(QtCore.QAbstractTableModel):
	def __init__(self, data, parent=None):
		super().__init__(parent=parent)
		self.data = data

	def rowCount(self, parent):
		if parent.isValid():
			return 0
		#print(len(self.data.keys()))
		return len(self.data.keys())

	def columnCount(self, parent):
		return len(self.data[list(self.data.keys())[0]])+1

	def data(self, index, role):
		if not index.isValid():
			return None
		elif role != QtCore.Qt.DisplayRole:
			return None
		else:
			key = list(self.data.keys())[index.row()]
			if index.column() == 0:
				return key
			else:
				return self.data[key][index.column()-1]

if __name__ == "__main__":
	global app

	atexit.register(pb_db_write)
	atexit.register(tsh_db_write)

	app = QtGui.QApplication(sys.argv)
	app.setApplicationName("pb_manager")
	app.setApplicationVersion("0.1")

	pbm = PBManager()
	pbm.show()
	sys.exit(app.exec_())
