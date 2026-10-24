import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

ColumnLayout {
    id: pane
    spacing: 10
    property var rarStatus: JSON.parse(nextBackend.rarStatusJson)
    FolderDialog { id: sourceDialog; title: "Juego que ya contiene game/tl"; onAccepted: backupProject.text = nextBackend.localPath(selectedFolder.toString()) }
    FileDialog { id: archiveDialog; fileMode: FileDialog.SaveFile; defaultSuffix: format.currentIndex === 1 ? "rar" : "zip"; nameFilters: format.currentIndex === 1 ? ["Respaldo RAR (*.rar)"] : ["Respaldo ZIP (*.zip)"]; onAccepted: backupOutput.text = nextBackend.localPath(selectedFile.toString()) }
    Label { text: "Respaldar traducciones existentes"; font.pixelSize: 20; font.bold: true }
    Label { text: "Funciona de forma independiente: comprime todos los idiomas presentes en game/tl y sus imágenes, con las mismas subcarpetas. No traduce el contenido de nuevo."; wrapMode: Text.Wrap; Layout.fillWidth: true; color: "#AAB3AD" }
    RowLayout {
        Layout.fillWidth: true
        TextField { id: backupProject; objectName: "backupProject"; Layout.fillWidth: true; placeholderText: "Origen del proyecto con las traducciones instaladas" }
        Button { text: "Origen"; onClicked: sourceDialog.open() }
    }
    RowLayout {
        Layout.fillWidth: true
        ComboBox { id: format; objectName: "backupFormat"; model: ["ZIP", "RAR"]; onCurrentIndexChanged: { if (backupOutput) backupOutput.text = backupOutput.text.replace(/\.(zip|rar)$/i,currentIndex === 1 ? ".rar" : ".zip") } }
        TextField { id: backupOutput; objectName: "backupOutput"; Layout.fillWidth: true; placeholderText: "Archivo de respaldo fuera de game/" }
        Button { text: "Destino"; onClicked: archiveDialog.open() }
    }
    Label { visible: format.currentIndex === 1; text: pane.rarStatus.reason; color: "#F5C15D"; wrapMode: Text.Wrap; Layout.fillWidth: true }
    Button { objectName: "exportIndependentBackup"; text: "Crear respaldo independiente"; enabled: !nextBackend.busy && backupProject.text.length > 0 && backupOutput.text.length > 0 && (format.currentIndex === 0 || pane.rarStatus.available); onClicked: nextBackend.exportBackup(backupProject.text,backupOutput.text) }
    Label { text: "Las imágenes traducidas deben estar en game/tl/<idioma>/ con su ruta relativa original. Si reemplazaste imágenes fuera de game/tl, este respaldo no las identifica automáticamente."; wrapMode: Text.Wrap; Layout.fillWidth: true; color: "#AAB3AD"; font.pixelSize: 11 }
}
