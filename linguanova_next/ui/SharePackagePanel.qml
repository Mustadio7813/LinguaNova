import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

ColumnLayout {
    id: pane
    property var jobs: JSON.parse(nextBackend.jobsJson).filter(j => j.has_output)
    property var selectedIds: []
    property var rarStatus: JSON.parse(nextBackend.rarStatusJson)
    spacing: 12
    FileDialog { id: outputDialog; fileMode: FileDialog.SaveFile; defaultSuffix: formatBox.currentIndex === 1 ? "rar" : "zip"; nameFilters: formatBox.currentIndex === 1 ? ["Traducción RAR (*.rar)"] : ["Traducción ZIP (*.zip)"]; onAccepted: outputField.text = nextBackend.localPath(selectedFile.toString()) }
    Label { text: "Empaquetar y compartir traducción"; font.pixelSize: 20; font.bold: true; color: "#F4F7F5" }
    Label { text: "Selecciona resultados del mismo proyecto y versión. Cada destino conserva sus subcarpetas y una única integración de Preferencias."; wrapMode: Text.Wrap; Layout.fillWidth: true; color: "#AAB3AD" }
    Repeater {
        model: pane.jobs
        CheckBox {
            objectName: "shareJob_" + modelData.job_id
            text: modelData.target + " · " + modelData.profile_id + " · " + modelData.project
            checked: pane.selectedIds.indexOf(modelData.job_id) >= 0
            Layout.fillWidth: true
            onToggled: {
                var items = pane.selectedIds.slice()
                if (checked && items.indexOf(modelData.job_id) < 0) items.push(modelData.job_id)
                if (!checked) items = items.filter(i => i !== modelData.job_id)
                pane.selectedIds = items
            }
        }
    }
    Label { visible: pane.jobs.length === 0; text: "Genera primero una traducción para habilitar esta utilidad."; color: "#F5C15D" }
    RowLayout {
        Label { text: "Formato"; color: "#F4F7F5" }
        ComboBox { id: formatBox; objectName: "shareArchiveFormat"; model: ["ZIP", "RAR"]; onCurrentIndexChanged: { if (outputField) outputField.text = outputField.text.replace(/\.(zip|rar)$/i, currentIndex === 1 ? ".rar" : ".zip") } }
    }
    Label { visible: formatBox.currentIndex === 1; text: pane.rarStatus.reason + " El destinatario solo descomprime y copia game/."; wrapMode: Text.Wrap; Layout.fillWidth: true; color: pane.rarStatus.available ? "#AAB3AD" : "#F5C15D" }
    RowLayout {
        Layout.fillWidth: true
        TextField { id: outputField; objectName: "shareOutput"; Layout.fillWidth: true; placeholderText: formatBox.currentIndex === 1 ? "Archivo RAR de destino" : "Archivo ZIP de destino" }
        Button { text: "Destino"; onClicked: outputDialog.open() }
    }
    Button { objectName: "previewShare"; text: "Revisar archivos, tamaño y validaciones"; enabled: pane.selectedIds.length > 0 && !nextBackend.busy; onClicked: preview.text = nextBackend.previewShare(JSON.stringify(pane.selectedIds)) }
    TextArea { id: preview; Layout.fillWidth: true; Layout.preferredHeight: 200; readOnly: true; selectByMouse: true; wrapMode: TextEdit.Wrap }
    Label { text: "Borrador experimental: ninguna prueba de tareas terminadas certifica la integración en un juego real ni su calidad editorial."; color: "#F5C15D"; wrapMode: Text.Wrap; Layout.fillWidth: true }
    Button { objectName: "exportShare"; text: "Crear paquete experimental"; enabled: pane.selectedIds.length > 0 && outputField.text.length > 0 && !nextBackend.busy && preview.text.length > 2 && (formatBox.currentIndex === 0 || pane.rarStatus.available); onClicked: nextBackend.exportShare(JSON.stringify(pane.selectedIds),outputField.text) }
}
