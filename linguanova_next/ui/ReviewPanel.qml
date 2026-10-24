import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: pane
    property var rows: JSON.parse(nextBackend.reviewJson)
    property var selected: null
    RowLayout {
    anchors.fill: parent
    spacing: 18
    ColumnLayout {
        Layout.preferredWidth: 360; Layout.maximumWidth: 420; Layout.fillHeight: true
        Label { text: "Entradas y pendientes"; font.pixelSize: 22; font.bold: true }
        ComboBox { id: jobSelect; Layout.fillWidth: true; model: JSON.parse(nextBackend.jobsJson); textRole: "job_id"; onActivated: nextBackend.loadJob(model[currentIndex].job_id) }
        ListView {
            Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 6; model: pane.rows
            delegate: ItemDelegate {
                width: ListView.view.width; height: 82
                contentItem: Column {
                    spacing: 4
                    Label { text: modelData.status + " · " + modelData.path + ":" + modelData.line; color: modelData.status === "accepted" ? "#B8F36B" : "#F5C15D"; font.pixelSize: 11; width: parent.width; elide: Text.ElideRight }
                    Label { text: modelData.original; width: parent.width; elide: Text.ElideRight }
                    Label { text: modelData.reasons.join(", "); width: parent.width; elide: Text.ElideRight; color: "#AAB3AD"; font.pixelSize: 11 }
                }
                onClicked: { pane.selected = modelData; correction.text = modelData.candidate; reason.text = "" }
            }
        }
    }
    ColumnLayout {
        Layout.fillWidth: true; Layout.fillHeight: true
        Label { text: "Revisión por ID"; font.pixelSize: 22; font.bold: true }
        Label { text: pane.selected ? pane.selected.occurrence_id : "Selecciona una entrada"; font.pixelSize: 10; color: "#AAB3AD"; Layout.fillWidth: true; elide: Text.ElideMiddle }
        TextArea { Layout.fillWidth: true; Layout.preferredHeight: 120; readOnly: true; text: pane.selected ? pane.selected.original + "\n\nContexto: " + pane.selected.context : ""; wrapMode: TextEdit.Wrap }
        Label { text: "Candidata / corrección" }
        TextArea { id: correction; Layout.fillWidth: true; Layout.preferredHeight: 130; wrapMode: TextEdit.Wrap; selectByMouse: true }
        TextField { id: reason; Layout.fillWidth: true; placeholderText: "Motivo contextual de la decisión" }
        CheckBox { id: editorial; text: "He revisado el idioma y su perfil editorial" }
        RowLayout {
            Button { text: "Validar corrección"; enabled: pane.selected !== null && !nextBackend.busy; onClicked: nextBackend.reviewEntry(JSON.stringify({occurrence_id:pane.selected.occurrence_id, decision:"correct", text:correction.text, reason:reason.text, editorial_approved:editorial.checked})) }
            Button { text: "Conservar original"; enabled: pane.selected !== null && !nextBackend.busy; onClicked: nextBackend.reviewEntry(JSON.stringify({occurrence_id:pane.selected.occurrence_id, decision:"preserve", reason:reason.text, editorial_approved:editorial.checked})) }
        }
        Label { text: "Las decisiones pasan de nuevo por validación al reanudar. Conservar un nombre no se cuenta como texto traducido."; wrapMode: Text.Wrap; color: "#AAB3AD"; Layout.fillWidth: true }
        Item { Layout.fillHeight: true }
    }
}
}
