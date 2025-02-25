#*****************************************************************************
#*   Copyright (c) 2014 Jonathan Wiedemann <wood.galaxy@gmail.com> (cutplan) *
#*   Copyright (c) 2019 Jerome Laverroux <jerome.laverroux@free.fr> (cutline)*
#*                                                                           *
#*   This program is free software; you can redistribute it and/or modify    *
#*   it under the terms of the GNU Lesser General Public License (LGPL)      *
#*   as published by the Free Software Foundation; either version 2 of       *
#*   the License, or (at your option) any later version.                     *
#*   for detail see the LICENCE text file.                                   *
#*                                                                           *
#*   This program is distributed in the hope that it will be useful,         *
#*   but WITHOUT ANY WARRANTY; without even the implied warranty of          *
#*   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the           *
#*   GNU Library General Public License for more details.                    *
#*                                                                           *
#*   You should have received a copy of the GNU Library General Public       *
#*   License along with this program; if not, write to the Free Software     *
#*   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307    *
#*   USA                                                                     *
#*                                                                           *
#*****************************************************************************

import FreeCAD
import Draft
import ArchCommands
if FreeCAD.GuiUp:
    import FreeCADGui
    from PySide import QtCore, QtGui
    from draftutils.translate import translate
else:
    # \cond
    def translate(ctxt,txt):
        return txt
    # \endcond

__title__="FreeCAD CutPlane"
__author__ = "Jonathan Wiedemann"
__url__ = "http://www.freecad.org"

## @package ArchCutPlane
#  \ingroup ARCH
#  \brief The Cut plane object and tools
#
#  This module handles the Cut Plane object

def getPlanWithLine(line):
    """Function to make a plane along Normal plan"""
    import Part
    import WorkingPlane
    plan = WorkingPlane.get_working_plane()
    w = plan.axis
    part = Part.Shape(line)
    out = part.extrude(w)
    return out


def cutComponentwithPlane(archObject, cutPlane, sideFace):
    """cut object from a plan define by a face, Behind = 0 , front = 1"""
    cutVolume = ArchCommands.getCutVolume(cutPlane, archObject.Object.Shape)
    if sideFace == 0:
        cutVolume = cutVolume[2]
    else:
        cutVolume = cutVolume[1]
    if cutVolume:
        obj = FreeCAD.ActiveDocument.addObject("Part::Feature","CutVolume")
        obj.Shape = cutVolume
        if "Additions" in archObject.Object.PropertiesList:
            ArchCommands.removeComponents(obj, archObject.Object) # Also changes the obj colors.
            return None
        else:
            Draft.format_object(obj, archObject.Object)
            cutObj = FreeCAD.ActiveDocument.addObject("Part::Cut","CutPlane")
            cutObj.Base = archObject.Object
            cutObj.Tool = obj
            return cutObj


class _CommandCutLine:
    "the Arch CutPlane command definition"
    def GetResources(self):
        return {"Pixmap": "Arch_CutLine",
                "MenuText": QtCore.QT_TRANSLATE_NOOP("Arch_CutLine", "Cut with line"),
                "ToolTip": QtCore.QT_TRANSLATE_NOOP("Arch_CutLine", "Cut an object with a line")}

    def IsActive(self):
        return len(FreeCADGui.Selection.getSelection()) > 1

    def Activated(self):
        sel = FreeCADGui.Selection.getSelectionEx()
        if len(sel) != 2:
            FreeCAD.Console.PrintError("You must select exactly two objects, the shape to be cut and a line\n")
            return
        if not sel[1].SubObjects:
            FreeCAD.Console.PrintError("You must select a line from the second object (cut line), not the whole object\n")
            return
        panel=_CutPlaneTaskPanel(linecut=True)
        FreeCADGui.Control.showDialog(panel)

class _CommandCutPlane:
    "the Arch CutPlane command definition"
    def GetResources(self):
       return {'Pixmap'  : 'Arch_CutPlane',
                'MenuText': QtCore.QT_TRANSLATE_NOOP("Arch_CutPlane","Cut with plane"),
                'ToolTip': QtCore.QT_TRANSLATE_NOOP("Arch_CutPlane","Cut an object with a plane")}

    def IsActive(self):
        return len(FreeCADGui.Selection.getSelection()) > 1

    def Activated(self):
        sel = FreeCADGui.Selection.getSelectionEx()
        if len(sel) != 2:
            FreeCAD.Console.PrintError("You must select exactly two objects, the shape to be cut and the cut plane\n")
            return
        if not sel[1].SubObjects:
            FreeCAD.Console.PrintError("You must select a face from the second object (cut plane), not the whole object\n")
            return
        panel=_CutPlaneTaskPanel()
        FreeCADGui.Control.showDialog(panel)

class _CutPlaneTaskPanel:
    def __init__(self,linecut=False):
        self.linecut=linecut
        self.plan=None
        if linecut:
            self.plan = getPlanWithLine(FreeCADGui.Selection.getSelectionEx()[1].SubObjects[0])
        else :
            self.plan = FreeCADGui.Selection.getSelectionEx()[1].SubObjects[0]

        self.form = QtGui.QWidget()
        self.form.setObjectName("TaskPanel")
        self.grid = QtGui.QGridLayout(self.form)
        self.grid.setObjectName("grid")
        self.title = QtGui.QLabel(self.form)
        self.grid.addWidget(self.title, 1, 0)
        self.infoText =  QtGui.QLabel(self.form)
        self.grid.addWidget(self.infoText, 2, 0)
        self.combobox = QtGui.QComboBox()
        self.combobox.setCurrentIndex(0)
        self.grid.addWidget(self.combobox, 2, 1)
        QtCore.QObject.connect(self.combobox,QtCore.SIGNAL("currentIndexChanged(int)"),self.previewCutVolume)
        self.previewObj = FreeCAD.ActiveDocument.addObject("Part::Feature","PreviewCutVolume")
        self.retranslateUi(self.form)
        self.previewCutVolume(self.combobox.currentIndex())

    def isAllowedAlterSelection(self):
        return False

    def accept(self):
        FreeCAD.ActiveDocument.removeObject(self.previewObj.Name)
        val = self.combobox.currentIndex()
        s = FreeCADGui.Selection.getSelectionEx()
        if len(s) > 1:
            if s[1].SubObjects:
                FreeCAD.ActiveDocument.openTransaction(translate("Arch","Cutting"))
                FreeCADGui.addModule("Arch")
                ###TODO redo FreeCADGui.doCommand by using self.plan:
                #FreeCADGui.doCommand("Arch.cutComponentwithPlane(FreeCADGui.Selection.getSelectionEx()[0],self.plan,"+ str(val) +")")
                cutComponentwithPlane(FreeCADGui.Selection.getSelectionEx()[0],self.plan,val)

                FreeCAD.ActiveDocument.commitTransaction()
                FreeCAD.ActiveDocument.recompute()
                return True
        FreeCAD.Console.PrintError("Wrong selection\n")
        return True

    def reject(self):
        FreeCAD.ActiveDocument.removeObject(self.previewObj.Name)
        FreeCAD.Console.PrintMessage("Cancel Cut Plane\n")
        return True

    def getStandardButtons(self):
        return int(QtGui.QDialogButtonBox.Ok|QtGui.QDialogButtonBox.Cancel)

    def previewCutVolume(self, i):
        cutVolume = ArchCommands.getCutVolume(self.plan,FreeCADGui.Selection.getSelectionEx()[0].Object.Shape)
        FreeCAD.ActiveDocument.removeObject(self.previewObj.Name)
        self.previewObj = FreeCAD.ActiveDocument.addObject("Part::Feature", "PreviewCutVolume")
        self.previewObj.ViewObject.ShapeColor = (1.00,0.00,0.00)
        self.previewObj.ViewObject.Transparency = 75
        if i == 1:
            cutVolume = cutVolume[1]
        else:
            cutVolume = cutVolume[2]
        if cutVolume:
            self.previewObj.Shape = cutVolume

    def retranslateUi(self, TaskPanel):
        TaskPanel.setWindowTitle(QtGui.QApplication.translate("Arch", "Cut Plane", None))
        self.title.setText(QtGui.QApplication.translate("Arch", "Cut Plane options", None))
        self.infoText.setText(QtGui.QApplication.translate("Arch", "Which side to cut", None))
        self.combobox.addItems([QtGui.QApplication.translate("Arch", "Behind", None),
                                    QtGui.QApplication.translate("Arch", "Front", None)])

if FreeCAD.GuiUp:
    FreeCADGui.addCommand('Arch_CutPlane',_CommandCutPlane())
    FreeCADGui.addCommand('Arch_CutLine', _CommandCutLine())
