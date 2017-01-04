from PyQt5 import QtGui, QtWidgets
import sys

class ImageWidget(QtWidgets.QWidget):

    def __init__(self, imagePath, parent):
        super(ImageWidget, self).__init__(parent)
        self.picture = QtGui.QPixmap(imagePath)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.drawPixmap(0, 0, self.picture)


class TableWidget(QtWidgets.QTableWidget):

    def setImage(self, row, col, imagePath):
        image = ImageWidget(imagePath, self)
        self.setCellWidget(row, col, image)

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    tableWidget = TableWidget(10, 2)
    tableWidget.setImage(0, 1, "icons/warn.png")
    tableWidget.show()
    sys.exit(app.exec_())