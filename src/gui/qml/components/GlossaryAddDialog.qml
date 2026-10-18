// SPDX-License-Identifier: GPL-3.0-or-later
// LinguaNova: modified work based on RenLocalizer 2.8.19; modification notice date 2026-10-16.
// See LICENSE/COPYING, NOTICE.md and MODIFICATIONS_LINGUANOVA.md.
// GlossaryAddDialog.qml — Reusable Glossary Addition Dialog
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Dialog {
    id: addGlossaryDialog
    anchors.centerIn: parent
    width: Math.min(460, parent ? parent.width * 0.85 : 460)
    padding: 0
    header: null
    footer: null
    modal: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    standardButtons: Dialog.NoButton

    property color clrCard: "#1F1A16"
    property color clrAccent: "#FF7A59"
    property color clrAccent2: "#FFB86B"
    property color clrTxt: "#F7F1EA"
    property color clrTxt2: "#B5A99D"
    property color clrTxtDim: "#8A7D72"
    property color clrInput: "#16120F"
    property color clrCardBorder: "#3A3029"

    function cleanTitle(str) {
        if (typeof root !== "undefined" && root.cleanModalTitle) {
            return root.cleanModalTitle(str);
        }
        return str || "";
    }

    enter: Transition {
        NumberAnimation { property: "opacity"; from: 0.0; to: 1.0; duration: 180; easing.type: Easing.OutCubic }
        NumberAnimation { property: "scale"; from: 0.94; to: 1.0; duration: 180; easing.type: Easing.OutCubic }
    }
    exit: Transition {
        NumberAnimation { property: "opacity"; from: 1.0; to: 0.0; duration: 140; easing.type: Easing.InQuad }
        NumberAnimation { property: "scale"; from: 1.0; to: 0.96; duration: 140; easing.type: Easing.InQuad }
    }

    Overlay.modal: Rectangle {
        color: Qt.rgba(0, 0, 0, 0.65)
    }

    background: Rectangle {
        color: addGlossaryDialog.clrCard
        radius: 18
        border.color: Qt.rgba(255, 122, 89, 0.45)
        border.width: 1.5
        clip: true

        Rectangle {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 3
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: addGlossaryDialog.clrAccent }
                GradientStop { position: 1.0; color: addGlossaryDialog.clrAccent2 }
            }
        }
    }

    contentItem: ColumnLayout {
        spacing: 16

        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 20
            Layout.rightMargin: 18
            Layout.topMargin: 20
            spacing: 14

            Rectangle {
                width: 40; height: 40; radius: 20
                color: Qt.rgba(255, 122, 89, 0.15)
                border.color: addGlossaryDialog.clrAccent; border.width: 1.5

                Label {
                    anchors.centerIn: parent
                    text: "📖"
                    font.pixelSize: 20
                }
            }

            ColumnLayout {
                spacing: 2
                Layout.fillWidth: true

                Label {
                    text: appBackend.uiTrigger, addGlossaryDialog.cleanTitle(appBackend.getTextWithDefault("glossary_dlg_add_title", "Sözlüğe Terim Ekle"))
                    font.pixelSize: 17; font.bold: true; color: addGlossaryDialog.clrTxt
                }
                Label {
                    text: appBackend.uiTrigger, appBackend.getTextWithDefault("glossary_dlg_add_sub", "Çevrilmeyecek veya özel çevrilecek terim tanımlayın")
                    font.pixelSize: 12; color: addGlossaryDialog.clrTxt2
                }
            }

            Rectangle {
                width: 30; height: 30; radius: 15
                color: closeGlossaryMa.containsMouse ? Qt.rgba(255, 255, 255, 0.12) : "transparent"
                scale: closeGlossaryMa.pressed ? 0.92 : (closeGlossaryMa.containsMouse ? 1.08 : 1.0)
                Behavior on scale { NumberAnimation { duration: 120 } }
                Behavior on color { ColorAnimation { duration: 120 } }

                Label {
                    anchors.centerIn: parent
                    text: "✕"
                    color: closeGlossaryMa.containsMouse ? "#FFFFFF" : addGlossaryDialog.clrTxtDim
                    font.pixelSize: 13; font.bold: true
                }
                MouseArea {
                    id: closeGlossaryMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: addGlossaryDialog.close()
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.leftMargin: 20
            Layout.rightMargin: 20
            Layout.preferredHeight: glossaryFormCol.implicitHeight + 24
            radius: 14
            color: addGlossaryDialog.clrInput
            border.color: Qt.rgba(255, 255, 255, 0.08)
            border.width: 1

            ColumnLayout {
                id: glossaryFormCol
                anchors.fill: parent
                anchors.margins: 14
                spacing: 10

                Label {
                    text: appBackend.uiTrigger, appBackend.getTextWithDefault("glossary_dlg_source", "Kaynak (Orijinal Metin):")
                    color: addGlossaryDialog.clrTxt
                    font.pixelSize: 12
                    font.bold: true
                }
                TextField {
                    id: addGlossarySource
                    Layout.fillWidth: true
                    height: 38
                    color: addGlossaryDialog.clrTxt
                    placeholderText: appBackend.getTextWithDefault("glossary_dlg_source_placeholder", "e.g. Character Name")
                    placeholderTextColor: addGlossaryDialog.clrTxtDim
                    font.pixelSize: 13
                    background: Rectangle {
                        radius: 10
                        color: "#0F0D0B"
                        border.color: addGlossarySource.activeFocus ? addGlossaryDialog.clrAccent : addGlossaryDialog.clrCardBorder
                        border.width: addGlossarySource.activeFocus ? 1.5 : 1
                        Behavior on border.color { ColorAnimation { duration: 150 } }
                    }
                }

                Label {
                    text: appBackend.uiTrigger, appBackend.getTextWithDefault("glossary_dlg_target", "Hedef (Çeviri):")
                    color: addGlossaryDialog.clrTxt
                    font.pixelSize: 12
                    font.bold: true
                }
                TextField {
                    id: addGlossaryTarget
                    Layout.fillWidth: true
                    height: 38
                    color: addGlossaryDialog.clrTxt
                    placeholderText: appBackend.getTextWithDefault("glossary_dlg_target_placeholder", "e.g. Karakter Adı")
                    placeholderTextColor: addGlossaryDialog.clrTxtDim
                    font.pixelSize: 13
                    background: Rectangle {
                        radius: 10
                        color: "#0F0D0B"
                        border.color: addGlossaryTarget.activeFocus ? addGlossaryDialog.clrAccent : addGlossaryDialog.clrCardBorder
                        border.width: addGlossaryTarget.activeFocus ? 1.5 : 1
                        Behavior on border.color { ColorAnimation { duration: 150 } }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 20
            Layout.rightMargin: 20
            Layout.bottomMargin: 20
            spacing: 12

            Button {
                Layout.fillWidth: true; height: 40
                scale: down ? 0.97 : (hovered ? 1.02 : 1.0)
                transformOrigin: Item.Center
                Behavior on scale { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
                onClicked: addGlossaryDialog.close()

                background: Rectangle {
                    radius: 12
                    color: parent.down ? Qt.rgba(255, 255, 255, 0.08) : (parent.hovered ? Qt.rgba(255, 255, 255, 0.05) : "transparent")
                    border.color: parent.hovered ? addGlossaryDialog.clrTxt2 : addGlossaryDialog.clrCardBorder
                    border.width: 1
                    Behavior on border.color { ColorAnimation { duration: 140 } }
                }
                contentItem: Label {
                    text: appBackend.uiTrigger, appBackend.getTextWithDefault("dialog_cancel", "İptal")
                    color: addGlossaryDialog.clrTxt2
                    font.pixelSize: 13
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }

            Button {
                id: addGlossarySubmitBtn
                Layout.preferredWidth: 130; height: 40
                scale: down ? 0.97 : (hovered ? 1.02 : 1.0)
                transformOrigin: Item.Center
                Behavior on scale { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
                onClicked: {
                    if (addGlossarySource.text.trim().length > 0) {
                        appBackend.addGlossaryItem(addGlossarySource.text.trim(), addGlossaryTarget.text.trim())
                        addGlossarySource.text = ""
                        addGlossaryTarget.text = ""
                        addGlossaryDialog.close()
                    }
                }

                background: Rectangle {
                    radius: 12
                    color: addGlossarySubmitBtn.hovered ? "#FFC987" : addGlossaryDialog.clrAccent
                    gradient: Gradient {
                        orientation: Gradient.Horizontal
                        GradientStop { position: 0.0; color: addGlossarySubmitBtn.hovered ? "#FFC987" : "#FF7A59" }
                        GradientStop { position: 1.0; color: addGlossarySubmitBtn.hovered ? "#FF7A59" : "#FFB86B" }
                    }
                    Behavior on color { ColorAnimation { duration: 140 } }
                }
                contentItem: Label {
                    text: appBackend.uiTrigger, "➕ " + appBackend.getTextWithDefault("glossary_add_btn", "Ekle")
                    color: "#0F0D0B"
                    font.bold: true
                    font.pixelSize: 13
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }
        }
    }
}
