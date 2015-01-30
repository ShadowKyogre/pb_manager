#!/usr/bin/env python3
from PyQt4 import QtCore, QtGui

from itertools import groupby
import atexit
import sys

from pb_manager import DB, TDB, tsh_paste, pb_paste, pb_update, \
                       pb_delete, pb_db_write, tsh_db_write, CFG

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

		self.tabview = QtGui.QTabWidget(self)
		self.tabview.addTab(self.ptpbtv, self.tr("ptpb.pw instance"))
		self.tabview.addTab(self.tshtv, self.tr("transfer.sh instance"))
		self.setCentralWidget(self.tabview)

		statusbar = self.statusBar()
		self.progress = QtGui.QProgressBar()
		self.progress.setFormat(self.tr("%v / %m files uploaded"))
		statusbar.addPermanentWidget(self.progress)

		self.opsbar = self.addToolBar(self.tr("Main"))
		action = self.opsbar.addAction(QtGui.QIcon.fromTheme("document-new"), 
		                               self.tr("New link(s)"))
		action.triggered.connect(self.new_link)

		action = self.opsbar.addAction(QtGui.QIcon.fromTheme("insert-link"), 
		                               self.tr("New ptpb.pw alias(es)"))
		action.triggered.connect(self.new_alias)

		action = self.opsbar.addAction(QtGui.QIcon.fromTheme("edit-delete"),
		                               self.tr("Delete link(s)"))
		action.triggered.connect(self.delete_link)

		action = self.opsbar.addAction(QtGui.QIcon.fromTheme("view-refresh"),
		                               self.tr("Update link(s)"))
		action.triggered.connect(self.update_link)
		orientation = CFG.get('GUI', 'TB_ORIENTATION', fallback='top')

		if orientation == 'right':
			self.addToolBar(QtCore.Qt.RightToolBarArea, self.opsbar)
		elif orientation == 'left':
			self.addToolBar(QtCore.Qt.LeftToolBarArea, self.opsbar)
		elif orientation == 'bottom':
			self.addTollBar(QtCore.Qt.BottomToolBarArea, self.opsbar)
		else:
			pass

	def new_alias(self):
		dialog = QtGui.QDialog()
		dialog.setWindowTitle(self.tr("Links to alias"))
		layout = QtGui.QVBoxLayout(dialog)
		te = QtGui.QPlainTextEdit(dialog)
		layout.addWidget(te)
		buttonbox = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
		buttonbox.accepted.connect(dialog.accept)
		buttonbox.rejected.connect(dialog.reject)
		layout.addWidget(buttonbox)
		result = dialog.exec()
		if result == QtGui.QDialog.Accepted:
			items = [QtCore.QUrl(l) for l in te.toPlainText().splitlines() ]
			print(items)
			self.ptpb_paste(items)

	def new_link(self):
		if self.tabview.currentWidget() == self.ptpbtv:
			files = QtGui.QFileDialog.getOpenFileNames(parent=self, 
			                                           caption=self.tr("Files to publicize"))
			items = [QtCore.QUrl(f) for f in files]
			print(items)
			result = QtGui.QMessageBox.question(self, self.tr("Public/Private?"), 
			                                    self.tr(("Are the files you are pasting"
			                                             " public (no) or private (yes)?")), 
			                                    buttons=QtGui.QMessageBox.Yes | \
			                                    QtGui.QMessageBox.No | \
			                                    QtGui.QMessageBox.Cancel)
			if result == QtGui.QMessageBox.Yes:
				self.ptpb_paste(items, private=True)
			elif result == QtGui.QMessageBox.No:
				self.ptpb_paste(items, private=False)
			else:
				pass

		elif self.tabview.currentWidget() == self.tshtv:
			files = QtGui.QFileDialog.getOpenFileNames(parent=self, 
			                                             caption=self.tr("Files to publicize"))
			items = [QtCore.QUrl(f) for f in files]
			print(items)

	def delete_link(self):
		if self.tabview.currentWidget() == self.tshtv:
			self.tsh_delete()
		elif self.tabview.currentWidget() == self.ptpbtv:
			self.ptpb_delete()

	def update_link(self):
		if self.tabview.currentWidget() == self.tshtv:
			self.tsh_update()
		elif self.tabview.currentWidget() == self.ptpbtv:
			self.ptpb_update()

	def eventFilter(self, obj, evt):
		if evt.type() == QtCore.QEvent.KeyPress:
			if evt.key() == QtCore.Qt.Key_Return:
				if obj == self.ptpbtv:
					self.ptpb_update()
				elif obj == self.tshtv:
					self.tsh_update()
			elif evt.key() == QtCore.Qt.Key_Delete:
				if obj == self.ptpbtv:
					self.ptpb_delete()
				elif obj == self.tshtv:
					self.tsh_delete()
			return super().eventFilter(obj, evt)
		return super().eventFilter(obj, evt)

	def ptpb_update(self):
		items = self.ptpbtv.selectedIndexes()[::4]
		for idx in items:
			print(idx.data(QtCore.Qt.DisplayRole))
			pb_update(idx.data(QtCore.Qt.DisplayRole))

	def tsh_update(self):
		items = self.tshtv.selectedIndexes()[::3]
		batch_items = [idx.data(QtCore.Qt.DisplayRole) for idx in items]
		tsh_paste(*batch_items, same_link=True)

	def tsh_delete(self):
		attop = QtCore.QModelIndex()
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

	def ptpb_paste(self, urls, private=False):
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
				pb_paste(url.toLocalFile(), private=private)
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
	QtGui.QIcon.setThemeName(CFG.get('GUI', 'ICON_THEME', 
	                                 fallback=QtGui.QIcon.themeName())
	                        )
	app.setApplicationName("pb_manager")
	app.setApplicationVersion("0.1")

	pbm = PBManager()
	pbm.show()

	app.installEventFilter(pbm)
	sys.exit(app.exec_())
