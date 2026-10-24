import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: card
    objectName: "linguanovaNextShareCard"
    required property var hostWindow
    Layout.fillWidth: true
    Layout.preferredHeight: content.implicitHeight + 2 * hostWindow.responsiveCardPadding
    implicitHeight: content.implicitHeight + 2 * hostWindow.responsiveCardPadding
    radius: 18; color: hostWindow.clrCard; border.color: hostWindow.clrCardBorder
    ColumnLayout {
        id: content
        anchors.fill: parent; anchors.margins: hostWindow.responsiveCardPadding
        spacing: hostWindow.responsiveCardSpacing
        Label { text: "Empaquetar y compartir traducción"; font.pixelSize: 18; font.bold: true; color: hostWindow.clrTxt; Layout.fillWidth: true; wrapMode: Text.Wrap }
        Label { text: "Resultados generados por la ampliación · destinos y perfiles separados · rutas conservadas"; color: hostWindow.clrTxt2; font.pixelSize: 12; Layout.fillWidth: true; wrapMode: Text.Wrap }
        RowLayout {
            Button { text: "Seleccionar proyecto e idiomas"; onClicked: nextBackend.showShare() }
            Button { text: "Abrir trabajos coordinados"; onClicked: nextBackend.showWork() }
        }
    }
}
