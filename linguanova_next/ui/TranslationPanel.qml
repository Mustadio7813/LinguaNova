import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

ScrollView {
    id: pane
    clip: true; contentWidth: availableWidth
    property var destinations: JSON.parse(nextBackend.listDestinations())
    property var profiles: JSON.parse(nextBackend.listSpanishProfiles())
    property var providers: JSON.parse(nextBackend.listProviders())
    property var settings: ({})
    property bool ready: false
    function contextChanged() {
        if (ready && target.currentIndex >= 0 && profile.currentIndex >= 0)
            nextBackend.selectDictionaryContext(projectField.text, destinations[target.currentIndex].id,
                target.currentIndex === 0 ? profiles[profile.currentIndex].id : "")
    }
    function jobPayload() {
        return {project: projectField.text, target: destinations[target.currentIndex].id,
            profile: target.currentIndex === 0 ? profiles[profile.currentIndex].id : "", spanish_profile: profiles[profile.currentIndex].id,
            provider: providers[provider.currentIndex].id, source: source.text, model: model.text,
            text_enabled: textCheck.checked,
            mode: mode.currentIndex === 0 ? "native" : "mod", recipe_path: recipeField.text,
            options: {endpoint: endpoint.text,
                allow_test_provider: providers[provider.currentIndex].id === "pseudo"}}
    }
    Component.onCompleted: {
        settings = JSON.parse(nextBackend.settingsJson)
        var ti = destinations.findIndex(d => d.id === settings.target)
        if (ti >= 0) target.currentIndex = ti
        var pi = profiles.findIndex(p => p.id === settings.profile)
        if (pi >= 0) profile.currentIndex = pi
        var ei = providers.findIndex(p => p.id === settings.provider)
        if (ei >= 0) provider.currentIndex = ei
        ready = true
        contextChanged()
    }
    FolderDialog { id: projectDialog; title: "Selecciona la copia del proyecto"; onAccepted: projectField.text = nextBackend.localPath(selectedFolder.toString()) }
    FileDialog { id: sourceFileDialog; title: "Selecciona RPA, RPY o RPYC dentro de game/"; nameFilters: ["Recursos Ren’Py (*.rpa *.rpy *.rpyc *.rpym *.rpymc)"]; onAccepted: projectField.text = nextBackend.localPath(selectedFile.toString()) }
    FileDialog { id: recipeDialog; title: "Receta de Preferencias verificada para este juego"; nameFilters: ["Receta (*.json)"]; onAccepted: recipeField.text = nextBackend.localPath(selectedFile.toString()) }
    ColumnLayout {
        width: pane.availableWidth; spacing: 16
        Label { text: "Un destino. Traducción de texto."; color: "#F4F7F5"; font.pixelSize: 24; font.bold: true }
        Label { text: "Selecciona una copia del juego. El texto traducido se revisa antes de compartir."; color: "#AAB3AD"; wrapMode: Text.Wrap; Layout.fillWidth: true }
        Frame {
            Layout.fillWidth: true
            background: Rectangle { color: "#14181D"; radius: 16; border.color: "#2A3139" }
            ColumnLayout {
                anchors.fill: parent; spacing: 12; enabled: !nextBackend.busy
                Label { text: "Origen del proyecto (copia del juego)"; font.bold: true }
                RowLayout {
                    Layout.fillWidth: true
                    TextField { id: projectField; objectName: "projectPath"; Layout.fillWidth: true; placeholderText: "Carpeta raíz del juego"; text: pane.settings.project || ""; onTextChanged: pane.contextChanged() }
                    Button { text: "Carpeta"; onClicked: projectDialog.open() }
                    Button { text: "Archivo"; onClicked: sourceFileDialog.open() }
                }
                GridLayout {
                    Layout.fillWidth: true; columns: pane.width < 1000 ? 2 : 4; columnSpacing: 16; rowSpacing: 8
                    Label { text: "Destino" }
                    ComboBox { id: target; objectName: "targetLanguage"; Layout.fillWidth: true; model: pane.destinations; textRole: "name"; onCurrentIndexChanged: pane.contextChanged() }
                    Label { text: "Perfil español"; visible: target.currentIndex === 0 }
                    ComboBox { id: profile; objectName: "spanishProfile"; Layout.fillWidth: true; model: pane.profiles; textRole: "name"; visible: target.currentIndex === 0; onCurrentIndexChanged: pane.contextChanged() }
                    Label { text: "Motor" }
                    ComboBox { id: provider; objectName: "translationProvider"; Layout.fillWidth: true; model: pane.providers.map(p => p.id === "pseudo" ? "pseudo · solo pruebas" : p.id) }
                    Label { text: "Origen del texto" }
                    TextField { id: source; Layout.fillWidth: true; text: pane.settings.source || "auto"; placeholderText: "auto, ja, de, en…" }
                    Label { text: "Modelo, si corresponde" }
                    TextField { id: model; Layout.fillWidth: true; placeholderText: "Predeterminado del proveedor" }
                    Label { text: "Endpoint opcional" }
                    TextField { id: endpoint; objectName: "providerEndpoint"; Layout.fillWidth: true; placeholderText: "Instancia LibreTranslate / API compatible" }
                }
                RowLayout {
                    CheckBox { id: textCheck; text: "Texto"; checked: true }
                    ComboBox { id: mode; model: ["Nativo", "MOD de interfaz aislado"] }
                    Item { Layout.fillWidth: true }
                }
                RowLayout {
                    Layout.fillWidth: true
                    TextField { id: recipeField; objectName: "preferencesRecipe"; Layout.fillWidth: true; placeholderText: "Receta de Preferencias del juego (sin receta, integración pendiente)" }
                    Button { text: "Receta"; onClicked: recipeDialog.open() }
                }
                Label { text: "Las claves se leen de variables LINGUANOVA_NEXT_<MOTOR>_KEY. Nunca se incluyen en el paquete del jugador."; color: "#AAB3AD"; font.pixelSize: 11; wrapMode: Text.Wrap; Layout.fillWidth: true }
                RowLayout {
                    Button { text: "Preparar Diccionario"; objectName: "prepareDictionary"; onClicked: { nextBackend.prepareDictionary(JSON.stringify(pane.jobPayload())); nextBackend.showDictionary() } }
                    Button { text: "Ver Diccionario"; onClicked: nextBackend.showDictionary() }
                }
                Label { text: "Al crear el trabajo se analiza primero el Diccionario. El mismo juego reutiliza el análisis; cada idioma conserva sus propias decisiones."; color: "#AAB3AD"; wrapMode: Text.Wrap; Layout.fillWidth: true }
                RowLayout {
                    Button {
                        text: "Crear trabajo y revisar resumen"; objectName: "createTranslationJob"; enabled: !nextBackend.busy
                        onClicked: nextBackend.createJob(JSON.stringify(pane.jobPayload()))
                    }
                    Button { text: "Iniciar trabajo creado"; objectName: "startTranslationJob"; enabled: !nextBackend.busy && nextBackend.currentJob.length > 0; onClicked: nextBackend.startJob(nextBackend.currentJob) }
                }
                Button { text: "Traducir los 5 idiomas"; objectName: "translateFiveLanguages"; enabled: !nextBackend.busy; onClicked: nextBackend.translateFiveLanguages(JSON.stringify(pane.jobPayload())) }
                Label { text: "El lote usa el perfil español seleccionado. Cada idioma genera sus propias imágenes y revisiones; después puedes empaquetarlos juntos en Utilidades."; color: "#AAB3AD"; wrapMode: Text.Wrap; Layout.fillWidth: true }
            }
        }
        Frame {
            Layout.fillWidth: true
            background: Rectangle { color: "#14181D"; border.color: "#2A3139"; radius: 16 }
            ColumnLayout {
                width: parent.width
                Label { text: "Resumen y cobertura"; font.pixelSize: 16; font.bold: true }
                TextArea { Layout.fillWidth: true; implicitHeight: 160; readOnly: true; text: JSON.stringify(JSON.parse(nextBackend.summaryJson), null, 2); wrapMode: TextEdit.Wrap; selectByMouse: true }
            }
        }
        Label { text: "Actividad real del trabajo"; font.bold: true }
        TextArea { Layout.fillWidth: true; implicitHeight: 160; text: nextBackend.activityText; readOnly: true; selectByMouse: true; wrapMode: TextEdit.Wrap }
    }
}
