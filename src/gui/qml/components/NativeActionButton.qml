import QtQuick
import QtQuick.Controls

Button {
    id: control
    required property var ui
    implicitHeight: 36
    implicitWidth: Math.max(100, label.implicitWidth + 28)
    background: Rectangle {
        radius: 8
        color: control.hovered ? control.ui.clrCardHover : control.ui.clrInput
        border.color: control.activeFocus ? control.ui.clrAccent : control.ui.clrCardBorder
        opacity: control.enabled ? 1 : 0.5
    }
    contentItem: Label {
        id: label
        text: control.text
        color: control.ui.clrTxt
        opacity: control.enabled ? 1 : 0.5
        font.pixelSize: 12
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
}
