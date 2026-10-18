// SPDX-License-Identifier: GPL-3.0-or-later
// LinguaNova: modified work based on RenLocalizer 2.8.19; modification notice date 2026-10-16.
// See LICENSE/COPYING, NOTICE.md and MODIFICATIONS_LINGUANOVA.md.
// ToastNotification.qml — Reusable Fluent Toast Notification Component
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: toast
    z: 999
    anchors.right: parent ? parent.right : undefined
    anchors.bottom: parent ? parent.bottom : undefined
    anchors.margins: 28
    width: Math.min(520, toastText.implicitWidth + 64)
    radius: 14
    height: Math.max(48, toastText.implicitHeight + 28)

    property string message: ""
    property string toastType: "info"

    property color clrSuccess: "#10B981"
    property color clrError: "#EF4444"
    property color clrWarn: "#F59E0B"
    property color clrAccent: "#FF7A59"
    property color clrTxt: "#F7F1EA"

    color: toastType === "success" ? "#064E3B" :
           toastType === "error"   ? "#7F1D1D" :
           toastType === "warning" ? "#78350F" : "#231C17"
    border.color: toastType === "success" ? clrSuccess :
                  toastType === "error"   ? clrError :
                  toastType === "warning" ? clrWarn : clrAccent
    border.width: 1.5

    opacity: 0.0
    visible: opacity > 0
    scale: opacity > 0 ? 1.0 : 0.94
    transformOrigin: Item.BottomRight
    transform: Translate {
        y: toast.opacity > 0 ? 0 : 14
        Behavior on y { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
    }
    Behavior on scale { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
    Behavior on opacity { NumberAnimation { duration: 200; easing.type: Easing.OutQuad } }

    function show(msg, type) {
        message = msg
        toastType = type || "info"
        opacity = 1.0
        toastTimer.restart()
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 12
        Label {
            text: toast.toastType === "success" ? "✓" :
                  toast.toastType === "error"   ? "✕" :
                  toast.toastType === "warning" ? "⚠️" : "ℹ"
            color: toast.toastType === "success" ? toast.clrSuccess :
                   toast.toastType === "error"   ? toast.clrError :
                   toast.toastType === "warning" ? toast.clrWarn : toast.clrAccent
            font.bold: true
            font.pixelSize: 15
        }
        Label {
            id: toastText
            text: toast.message
            color: toast.clrTxt
            font.pixelSize: 13
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
        }
    }
    Timer {
        id: toastTimer
        interval: 3500
        onTriggered: toast.opacity = 0.0
    }
}
