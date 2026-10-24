import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: pane
    property var dictionary: JSON.parse(nextBackend.dictionaryJson)
    property var rows: dictionary.entries || []
    property var selected: null
    onDictionaryChanged: selected = null
    ColumnLayout {
        anchors.fill: parent; spacing: 12
        Label { text: "Diccionario del proyecto"; font.pixelSize: 24; font.bold: true }
        Label { text: pane.dictionary.project ? pane.dictionary.project + " · " + pane.dictionary.target.locale : "Vacío. Selecciona el origen en Traducción y prepara el Diccionario o crea un trabajo."; wrapMode: Text.Wrap; color: "#AAB3AD"; Layout.fillWidth: true }
        Label { visible: !!pane.dictionary.project; text: (pane.dictionary.reused ? "Análisis reutilizado" : "Análisis actualizado") + " · " + (pane.dictionary.files || 0) + " archivos · " + (pane.dictionary.inventory_count || 0) + " textos inventariados"; color: "#B8F36B" }
        Label { visible: (pane.dictionary.stale_choices || 0) > 0; text: "Hay " + (pane.dictionary.stale_choices || 0) + " decisiones de una versión anterior del juego. Revísalas antes de volver a utilizarlas."; color: "#F5C15D"; wrapMode: Text.Wrap; Layout.fillWidth: true }
        Label { text: "El análisis se conserva por juego. Las decisiones se guardan por idioma y perfil. Los nombres se reconocen por sus declaraciones; los términos repetidos necesitan una decisión para imponer su traducción."; wrapMode: Text.Wrap; color: "#AAB3AD"; Layout.fillWidth: true }
        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 18
            ListView {
                objectName: "dictionaryList"
                Layout.preferredWidth: 340; Layout.fillHeight: true; clip: true; spacing: 6; model: pane.rows
                delegate: ItemDelegate {
                    required property var modelData
                    width: ListView.view.width; height: 74
                    contentItem: Column {
                        Label { text: modelData.source; width: parent.width; elide: Text.ElideRight }
                        Label { text: modelData.kind === "character" ? "Nombre declarado · contexto limitado" : "Término repetido · revisión"; color: "#AAB3AD"; font.pixelSize: 11 }
                        Label { text: modelData.choice ? modelData.choice.text : "Sin decisión manual para este idioma"; color: "#F5C15D"; width: parent.width; elide: Text.ElideRight }
                    }
                    onClicked: { pane.selected = modelData; translated.text = modelData.choice ? modelData.choice.text : modelData.source; reason.text = modelData.choice ? modelData.choice.reason : "" }
                }
            }
            ColumnLayout {
                Layout.fillWidth: true; Layout.fillHeight: true
                Label { text: pane.selected ? pane.selected.source : "Selecciona un nombre o término"; font.pixelSize: 18; font.bold: true }
                TextArea { Layout.fillWidth: true; Layout.preferredHeight: 100; readOnly: true; wrapMode: TextEdit.Wrap; text: pane.selected ? pane.selected.evidence.map(e => e.path + ":" + e.line).join("\n") : "" }
                TextField { id: translated; objectName: "dictionaryTranslation"; Layout.fillWidth: true; placeholderText: "Traducción requerida para este idioma" }
                TextField { id: reason; objectName: "dictionaryReason"; Layout.fillWidth: true; placeholderText: "Motivo de la decisión" }
                RowLayout {
                    Button { text: "Guardar traducción"; enabled: pane.selected !== null && !nextBackend.busy; onClicked: nextBackend.saveDictionaryChoice(JSON.stringify({id:pane.selected.id,decision:"translate",text:translated.text,reason:reason.text})) }
                    Button { text: "Conservar término"; enabled: pane.selected !== null && !nextBackend.busy; onClicked: nextBackend.saveDictionaryChoice(JSON.stringify({id:pane.selected.id,decision:"preserve",text:pane.selected.source,reason:reason.text})) }
                }
                Label { text: "Las decisiones nuevas se aplican al crear el siguiente trabajo. La conservación se contabiliza aparte del texto traducido."; wrapMode: Text.Wrap; color: "#F5C15D"; Layout.fillWidth: true }
                TextArea { visible: (pane.dictionary.diagnostics || []).length > 0; Layout.fillWidth: true; Layout.fillHeight: true; readOnly: true; wrapMode: TextEdit.Wrap; text: "Límites del análisis:\n" + JSON.stringify(pane.dictionary.diagnostics || [],null,2) }
                Item { Layout.fillHeight: true }
            }
        }
        RowLayout {
            Button { text: "Volver a Traducción"; onClicked: nextBackend.showWork() }
            Button { text: "Vaciar vista"; enabled: !nextBackend.busy; onClicked: nextBackend.clearDictionaryView() }
            Label { text: "La vista se inicia vacía al abrir el programa."; color: "#AAB3AD"; font.pixelSize: 11 }
        }
    }
}
