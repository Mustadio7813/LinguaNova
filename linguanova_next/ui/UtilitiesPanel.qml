import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ScrollView {
    id: pane
    contentWidth: availableWidth
    clip: true
    ColumnLayout {
        width: pane.availableWidth
        spacing: 18
        Label { text: "Utilidades"; font.pixelSize: 24; font.bold: true }
        Frame {
            Layout.fillWidth: true
            background: Rectangle { color: "#14181D"; border.color: "#2A3139"; radius: 18 }
            SharePackagePanel { width: parent.width }
        }
        Frame {
            Layout.fillWidth: true
            background: Rectangle { color: "#14181D"; border.color: "#2A3139"; radius: 18 }
            BackupPanel { width: parent.width }
        }
        Frame {
            Layout.fillWidth: true
            background: Rectangle { color: "#14181D"; border.color: "#2A3139"; radius: 18 }
            ColumnLayout {
                width: parent.width
                Label { text: "Herramientas clásicas"; font.bold: true }
                Label { text: "Abre la interfaz clásica para acceder a las herramientas de traducción existentes."; color: "#AAB3AD"; wrapMode: Text.Wrap; Layout.fillWidth: true }
                Button { text: "Abrir aplicación clásica"; enabled: !nextBackend.busy; onClicked: nextBackend.openClassic() }
            }
        }
    }
}
