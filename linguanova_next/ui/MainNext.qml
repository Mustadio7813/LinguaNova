import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

ApplicationWindow {
    id: root
    objectName: "linguanovaNextWindow"
    width: 1280; height: 850; minimumWidth: 840; minimumHeight: 620
    visible: true; title: "LinguaNova · Traducción de texto y respaldo"
    color: "#0B0D10"
    Material.theme: Material.Dark; Material.accent: "#B8F36B"; Material.primary: "#12161B"
    property int pageIndex: 0
    header: ColumnLayout {
        spacing: 0
        Rectangle {
            Layout.fillWidth: true; implicitHeight: 82; color: "#101318"
            RowLayout {
                anchors.fill: parent; anchors.margins: 22; spacing: 18
                ColumnLayout {
                    Label { text: "LinguaNova"; color: "#F4F7F5"; font.pixelSize: 26; font.bold: true }
                    Label { text: "MULTIDIOMA EXPERIMENTAL   /   Base 1.1.2 intacta"; color: "#AAB3AD"; font.pixelSize: 11 }
                }
                Item { Layout.fillWidth: true }
                Label { text: nextBackend.busy ? "● Trabajo activo" : "● Preparado"; color: "#B8F36B" }
                Button { text: "Aplicación clásica"; enabled: !nextBackend.busy; onClicked: nextBackend.openClassic() }
            }
        }
        TabBar {
            Layout.fillWidth: true; currentIndex: root.pageIndex
            onCurrentIndexChanged: root.pageIndex = currentIndex
            TabButton { text: "Traducción" }
            TabButton { text: "Revisión textual" }
            TabButton { text: "Utilidades" }
            TabButton { text: "Diccionario" }
        }
    }
    ColumnLayout {
        anchors.fill: parent; anchors.margins: 20; spacing: 12
        Rectangle {
            visible: nextBackend.error.length > 0
            Layout.fillWidth: true; implicitHeight: errorLabel.implicitHeight + 24
            color: "#302027"; border.color: "#FF6B7A"; radius: 10
            Label { id: errorLabel; anchors.fill: parent; anchors.margins: 12; text: nextBackend.error; color: "#FFB7C0"; wrapMode: Text.Wrap }
        }
        StackLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; currentIndex: root.pageIndex
            TranslationPanel { }
            ReviewPanel { }
            UtilitiesPanel { }
            DictionaryPanel { }
        }
        RowLayout {
            Layout.fillWidth: true
            Label { text: nextBackend.currentJob ? "Trabajo: " + nextBackend.currentJob : "Cada trabajo fija un único destino para la traducción de texto."; color: "#AAB3AD"; font.pixelSize: 11; Layout.fillWidth: true }
            Button { visible: nextBackend.busy; text: "Cancelar"; onClicked: nextBackend.cancelJob() }
            Button { objectName: "resumeTranslationJob"; visible: nextBackend.currentJob.length > 0; enabled: !nextBackend.busy; text: "Reanudar y validar"; onClicked: nextBackend.startJob(nextBackend.currentJob) }
        }
    }
}
