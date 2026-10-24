import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

Rectangle {
    id: card
    objectName: "nativePackageCard"
    required property var ui
    implicitHeight: content.implicitHeight + 32
    radius: 16
    color: ui.clrCard
    border.color: ui.clrCardBorder
    function t(key, fallback) { var refresh = appBackend.uiTrigger; return appBackend.getTextWithDefault(key, fallback) }
    ColumnLayout {
        id: content
        anchors.fill: parent; anchors.margins: 16; spacing: 9
        Label {
            text: card.t("native_package_title", "Share or back up translations")
            color: card.ui.clrTxt; font.pixelSize: 16; font.bold: true
        }
        Label {
            Layout.fillWidth: true
            text: card.t("native_package_description", "Select the game in Translation. Save its installed languages, translated images and language helpers in one ZIP/RAR, preserving game/tl and every subfolder. The package can be copied onto the same game version.")
            color: card.ui.clrTxt2; font.pixelSize: 12; wrapMode: Text.WordWrap
        }
        NativeActionButton {
                ui: card.ui
            objectName: "nativeCreatePackage"
            text: card.t("native_package_create", "Create ZIP / RAR")
            enabled: !appBackend.images.busy && !ui.isTranslating && !appBackend.modRunning
            Layout.preferredHeight: 40
            onClicked: destinationPicker.open()
        }
        Label {
            Layout.fillWidth: true
            text: appBackend.images.status
            color: card.ui.clrTxt2; wrapMode: Text.WrapAnywhere; font.pixelSize: 11
        }
    }
    FileDialog {
        id: destinationPicker
        fileMode: FileDialog.SaveFile
        defaultSuffix: "zip"
        nameFilters: ["ZIP (*.zip)", "RAR (*.rar)"]
        title: card.t("native_package_create", "Create ZIP / RAR")
        onAccepted: appBackend.images.createPackage(selectedFile.toString())
    }
}
