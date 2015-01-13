from PyQt4 import QtCore, QtGui

from itertools import groupby
import atexit
import sys

from pb_manager import DB, TDB, tsh_paste, pb_paste, pb_update, \
                       pb_delete, pb_db_write, tsh_db_write

class PBManager(QtGui.QMainWindow):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.tshtv = UrlDropPlace(self)
		self.tshtv.setModel(TSHModel(TDB))
		self.tshtv.setDragDropMode(QtGui.QAbstractItemView.DropOnly)
		self.tshtv.setAcceptDrops(True)

		self.ptpbtv = UrlDropPlace(self)
		self.ptpbtv.setModel(PTPBModel(DB))
		self.ptpbtv.setDragDropMode(QtGui.QAbstractItemView.DropOnly)
		self.ptpbtv.setAcceptDrops(True)

		self.ptpbtv.dropped.connect(self.ptpb_paste)
		self.tshtv.dropped.connect(self.tsh_paste)

		tabview = QtGui.QTabWidget(self)
		tabview.addTab(self.ptpbtv, "ptpb.pw instance")
		tabview.addTab(self.tshtv, "transfer.sh instance")
		self.setCentralWidget(tabview)

		statusbar = self.statusBar()
		self.progress = QtGui.QProgressBar()
		self.progress.setFormat("%v / %m files uploaded")
		statusbar.addPermanentWidget(self.progress)

	def eventFilter(self, obj, evt):
		if evt.type() == QtCore.QEvent.KeyPress:
			if evt.key() == QtCore.Qt.Key_Return:
				if obj == self.ptpbtv:
					items = self.ptpbtv.selectedIndexes()[::4]
					for idx in items:
						print(idx.data(QtCore.Qt.DisplayRole))
						pb_update(idx.data(QtCore.Qt.DisplayRole))
				elif obj == self.tshtv:
					items = self.tshtv.selectedIndexes()[::3]
					batch_items = [idx.data(QtCore.Qt.DisplayRole) for idx in items]
					tsh_paste(*batch_items, same_link=True)
			elif evt.key() == QtCore.Qt.Key_Delete:
				if obj == self.ptpbtv:
					self.ptpb_delete()
				elif obj == self.tshtv:
					self.tsh_delete()
			return super().eventFilter(obj, evt)
		return super().eventFilter(obj, evt)

	def tsh_delete(self):
		attop=QtCore.QModelIndex()
		items = self.tshtv.selectedIndexes()[::3]
		for k, g in groupby(enumerate(items), key=lambda x: x[0]-x[1].row()):
			conseg_grp = list(g)
			self.tshtv.model().beginRemoveRows(attop, conseg_grp[0][1].row(), 
						                       conseg_grp[-1][1].row())
			for item in conseg_grp:
				del TDB[item[1].data(QtCore.Qt.DisplayRole)]
			self.tshtv.model().endRemoveRows()

	def ptpb_delete(self):
		attop=QtCore.QModelIndex()
		items = self.ptpbtv.selectedIndexes()[::4]
		#http://stackoverflow.com/questions/2361945/detecting-consecutive-integers-in-a-list
		for k, g in groupby(enumerate(items), key=lambda x: x[0]-x[1].row()):
			conseg_grp = list(g)
			self.ptpbtv.model().beginRemoveRows(attop, conseg_grp[0][1].row(), 
			                                    conseg_grp[-1][1].row())
			pb_delete(*[ iidx[1].data(QtCore.Qt.DisplayRole) \
			             for iidx in conseg_grp ])
			self.ptpbtv.model().endRemoveRows()

	def ptpb_paste(self, urls):
		attop=QtCore.QModelIndex()
		lastrow=self.ptpbtv.model().rowCount(attop)+1
		lastnewrow=len(urls)+lastrow
		self.ptpbtv.model().beginInsertRows(attop, lastrow, lastnewrow)
		i = 0
		self.progress.setRange(0, lastnewrow-lastrow)
		self.progress.setValue(i)
		for url in urls:
			if url.toLocalFile() == "":
				pb_paste(url.toString(), alias=True)
			else:
				pb_paste(url.toLocalFile())
			i+=1
			self.progress.setValue(i)
		self.ptpbtv.model().endInsertRows()
		self.progress.reset()
		#print(urls)

	def tsh_paste(self, urls):
		attop=QtCore.QModelIndex()
		lastrow=self.tshtv.model().rowCount(attop)+1
		lastnewrow=len(urls)+lastrow
		self.tshtv.model().beginInsertRows(attop, lastrow, lastnewrow)
		batch_list=[]
		self.progress.setRange(0, lastnewrow-lastrow)
		self.progress.setValue(0)
		for url in urls:
			if url.toLocalFile() != "":
				batch_list.append(url.toLocalFile())
		tsh_paste(*batch_list, same_link=True)
		self.progress.setValue(self.progress.maximum())
		self.progress.reset()
		self.tshtv.model().endInsertRows()

#http://stackoverflow.com/questions/4151637/pyqt4-drag-and-drop-files-into-qlistwidget
class UrlDropPlace(QtGui.QTreeView):
	dropped = QtCore.pyqtSignal(list)
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
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

class PTPBModel(DBTableModel):
	HEADERS=["Filename/URL", "Public URL", "UUID", "Private?"]
	def headerData(self, col, orientation, role):
		if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
			try:
				return self.HEADERS[col]
			except IndexError:
					pass
		return super().headerData(col, orientation, role)

class TSHModel(DBTableModel):
	HEADERS=["Filename/URL", "Public URL", "Post Date"]
	def headerData(self, col, orientation, role):
		#print(orientation, role)
		if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
			try:
				return self.HEADERS[col]
			except IndexError:
				pass
		return super().headerData(col, orientation, role)

if __name__ == "__main__":
	global app

	atexit.register(pb_db_write)
	atexit.register(tsh_db_write)

	app = QtGui.QApplication(sys.argv)
	app.setApplicationName("pb_manager")
	app.setApplicationVersion("0.1")

	pbm = PBManager()
	pbm.show()

	app.installEventFilter(pbm)
	sys.exit(app.exec_())
