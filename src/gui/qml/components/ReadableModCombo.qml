import QtQuick
import QtQuick.Controls

ComboBox {
    id: control
    property color fieldColor: "#0f1419"
    property color popupColor: "#151c23"
    property color textColor: "#eef3f7"
    property color borderColor: "#34414b"
    property color accentColor: "#b8f36b"
    implicitHeight: 44
    implicitWidth: 240
    font.pixelSize: 13
    leftPadding: 14
    rightPadding: 36
    topPadding: 10
    bottomPadding: 10
    contentItem: Label {
        text: control.displayText
        font: control.font
        color: control.textColor
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
    indicator: Label {
        x: control.width - width - 14
        y: (control.height - height) / 2
        text: "▾"
        color: control.textColor
        font.pixelSize: 16
    }
    background: Rectangle {
        color: control.fieldColor
        radius: 10
        border.color: control.activeFocus ? control.accentColor : control.borderColor
        border.width: 1
    }
    delegate: ItemDelegate {
        id: row
        width: control.width - 12
        height: 42
        highlighted: control.highlightedIndex === index
        hoverEnabled: true
        text: control.textRole ? modelData[control.textRole] : modelData
        contentItem: Label {
            text: row.text
            color: control.currentIndex === index ? control.accentColor : control.textColor
            font.pixelSize: 13
            font.bold: control.currentIndex === index
            leftPadding: 12
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        background: Rectangle {
            radius: 7
            color: row.highlighted || row.hovered ? Qt.rgba(control.accentColor.r,control.accentColor.g,control.accentColor.b,0.14) : "transparent"
        }
    }
    popup: Popup {
        y: control.height + 6
        width: control.width
        padding: 6
        implicitHeight: Math.min(contentItem.implicitHeight + 12, 300)
        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: control.delegateModel
            currentIndex: control.highlightedIndex
            ScrollBar.vertical: ScrollBar { }
        }
        background: Rectangle {
            color: control.popupColor
            radius: 10
            border.color: control.borderColor
            border.width: 1
        }
    }
}
