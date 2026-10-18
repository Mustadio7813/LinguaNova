// SPDX-License-Identifier: GPL-3.0-or-later
// LinguaNova: modified work based on RenLocalizer 2.8.19; modification notice date 2026-10-16.
// See LICENSE/COPYING, NOTICE.md and MODIFICATIONS_LINGUANOVA.md.
// AboutDialog.qml — Diálogo "Acerca de" de LinguaNova
// Muestra versión, descripción y la atribución exigida por la licencia GPL-3.0.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Dialog {
    id: aboutDialog
    anchors.centerIn: parent
    width: Math.min(520, parent ? parent.width * 0.88 : 520)
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
    property color clrInput: "#16120F"
    property color clrBorder: "#3A3029"

    enter: Transition {
        NumberAnimation { property: "opacity"; from: 0.0; to: 1.0; duration: 180; easing.type: Easing.OutCubic }
        NumberAnimation { property: "scale"; from: 0.94; to: 1.0; duration: 180; easing.type: Easing.OutCubic }
    }
    exit: Transition {
        NumberAnimation { property: "opacity"; from: 1.0; to: 0.0; duration: 140; easing.type: Easing.InQuad }
    }

    Overlay.modal: Rectangle { color: Qt.rgba(0, 0, 0, 0.65) }

    background: Rectangle {
        color: aboutDialog.clrCard
        radius: 22
        border.color: aboutDialog.clrBorder
        border.width: 1
        clip: true

        Rectangle {
            anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right
            height: 4
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: aboutDialog.clrAccent }
                GradientStop { position: 1.0; color: aboutDialog.clrAccent2 }
            }
        }
    }

    contentItem: ColumnLayout {
        spacing: 16

        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 24; Layout.rightMargin: 20; Layout.topMargin: 26
            spacing: 16

            Image {
                Layout.preferredWidth: 64; Layout.preferredHeight: 64
                source: appBackend.get_asset_url("linguanova_logo.png")
                sourceSize: Qt.size(128, 128)
                fillMode: Image.PreserveAspectFit
                smooth: true; mipmap: true
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4
                Label {
                    text: appBackend.uiTrigger, appBackend.getTextWithDefault("app_title", "LinguaNova")
                    font.pixelSize: 24; font.bold: true; color: aboutDialog.clrTxt
                }
                Label {
                    text: "v" + appBackend.version + "  ·  GPL-3.0"
                    font.pixelSize: 12; font.bold: true; color: aboutDialog.clrAccent
                }
            }

            Button {
                Layout.alignment: Qt.AlignTop
                implicitWidth: 30; implicitHeight: 30
                onClicked: aboutDialog.close()
                background: Rectangle {
                    radius: 15
                    color: parent.hovered ? Qt.rgba(255, 255, 255, 0.12) : "transparent"
                }
                contentItem: Label {
                    text: "✕"; font.pixelSize: 13; font.bold: true
                    color: parent.hovered ? "#FFFFFF" : aboutDialog.clrTxt2
                    horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.leftMargin: 24; Layout.rightMargin: 24
            Layout.preferredHeight: descLbl.implicitHeight + 28
            radius: 18
            color: aboutDialog.clrInput
            border.color: aboutDialog.clrBorder; border.width: 1
            Label {
                id: descLbl
                anchors.fill: parent; anchors.margins: 14
                text: appBackend.uiTrigger, appBackend.getTextWithDefault("app_description",
                      "Translation tool for Ren'Py games.")
                color: aboutDialog.clrTxt
                wrapMode: Text.Wrap; font.pixelSize: 13; lineHeight: 1.3
            }
        }

        Label {
            Layout.fillWidth: true
            Layout.leftMargin: 24; Layout.rightMargin: 24
            text: appBackend.uiTrigger, appBackend.getTextWithDefault("about_attribution",
                  "LinguaNova is free software under GNU GPL v3 or later and is a modified version of RenLocalizer.")
            color: aboutDialog.clrTxt2
            wrapMode: Text.Wrap; font.pixelSize: 11; lineHeight: 1.25
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.leftMargin: 24; Layout.rightMargin: 24
            Layout.preferredHeight: legalCol.implicitHeight + 22
            radius: 14
            color: aboutDialog.clrInput
            border.color: aboutDialog.clrBorder
            border.width: 1

            ColumnLayout {
                id: legalCol
                anchors.fill: parent
                anchors.margins: 11
                spacing: 5

                Label {
                    Layout.fillWidth: true
                    text: appBackend.uiTrigger, appBackend.getTextWithDefault("about_modified_notice",
                              "Modified work based on RenLocalizer 2.8.19 · Modification notice: 2026-10-16")
                    color: aboutDialog.clrTxt
                    wrapMode: Text.Wrap; font.pixelSize: 10; font.bold: true
                }
                Label {
                    Layout.fillWidth: true
                    text: appBackend.uiTrigger, appBackend.getTextWithDefault("about_license_notice",
                              "License: GNU GPL v3 or later. See LICENSE/COPYING and NOTICE.md.")
                    color: aboutDialog.clrTxt2
                    wrapMode: Text.Wrap; font.pixelSize: 10
                }
                Label {
                    Layout.fillWidth: true
                    text: appBackend.uiTrigger, appBackend.getTextWithDefault("about_source_notice",
                              "If you receive a binary, you are entitled to the corresponding source under the GPL terms.")
                    color: aboutDialog.clrTxt2
                    wrapMode: Text.Wrap; font.pixelSize: 10
                }
                Label {
                    Layout.fillWidth: true
                    text: appBackend.uiTrigger, appBackend.getTextWithDefault("about_no_warranty",
                              "No warranty is provided, to the extent permitted by law.")
                    color: aboutDialog.clrTxt2
                    wrapMode: Text.Wrap; font.pixelSize: 10
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 24; Layout.rightMargin: 24; Layout.bottomMargin: 22
            Item { Layout.fillWidth: true }
            Button {
                Layout.preferredWidth: 120; implicitHeight: 40
                onClicked: aboutDialog.close()
                background: Rectangle {
                    radius: 14
                    gradient: Gradient {
                        orientation: Gradient.Horizontal
                        GradientStop { position: 0.0; color: aboutDialog.clrAccent }
                        GradientStop { position: 1.0; color: aboutDialog.clrAccent2 }
                    }
                    opacity: parent.hovered ? 0.9 : 1.0
                }
                contentItem: Label {
                    text: appBackend.uiTrigger, appBackend.getTextWithDefault("dialog_ok", "OK")
                    color: "#14110F"; font.bold: true; font.pixelSize: 13
                    horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                }
            }
        }
    }
}
