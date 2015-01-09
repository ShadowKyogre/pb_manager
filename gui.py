from PyQt4 import QtCore, QtGui

import atexit
import sys

from pb_manager import DB, TDB, tsh_paste, pb_paste, pb_update, \
                       pb_delete, pb_db_write, tsh_db_write

class PBManager(QtGui.QMainWindow):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		tshtv = QtGui.QTreeView(self)
		tshtv.setModel(DBTableModel(TDB))

		ptpbtv = QtGui.QTreeView(self)
		ptpbtv.setModel(DBTableModel(DB))

		tabview = QtGui.QTabWidget(self)
		tabview.addTab(ptpbtv, "ptpb.pw instance")
		tabview.addTab(tshtv, "transfer.sh instance")
		self.setCentralWidget(tabview)

class DBTableModel(QtCore.QAbstractTableModel):
	def __init__(self, data, parent=None):
		super().__init__(parent=parent)
		self.data = data

	def rowCount(self, parent):
		if parent.isValid():
			return 0
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
