// SPDX-License-Identifier: GPL-3.0-or-later
// LinguaNova: modified work based on RenLocalizer 2.8.19; modification notice date 2026-10-16.
// See LICENSE/COPYING, NOTICE.md and MODIFICATIONS_LINGUANOVA.md.
// Main.qml — LinguaNova Workspace UI
// Interfaz reconstruida como un espacio de trabajo horizontal.
// El núcleo Python, señales, motores y flujo de traducción se conservan sin cambios.
import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import QtQuick.Dialogs
import QtQuick.Window
import "components"

ApplicationWindow {
    id: root
    title: appBackend.uiTrigger, appBackend.getTextWithDefault("app_title", "LinguaNova") + " (" + appBackend.version + ")"

    // Responsive desktop geometry.
    // The Python launcher opens the window maximized; these values are the safe
    // fallback for windowed mode and for unusually small desktop work areas.
    width: Math.max(760, Math.min(1420, Screen.desktopAvailableWidth * 0.96))
    height: Math.max(560, Math.min(900, Screen.desktopAvailableHeight * 0.96))
    minimumWidth: Math.min(760, Screen.desktopAvailableWidth)
    minimumHeight: Math.min(560, Screen.desktopAvailableHeight)
    visible: false // Python shows the window after QML is fully loaded.

    // Global responsive breakpoints. All main workspaces use these values so
    // maximizing LinguaNova is sufficient on 1366x768, 1600x900, Full HD,
    // ultrawide and high-DPI desktop work areas.
    readonly property bool compactHeight: height <= 820
    readonly property bool compactWidth: width <= 1180
    readonly property bool narrowWidth: width <= 920
    readonly property bool veryNarrowWidth: width <= 800

    // 1080p-class work areas get a slightly denser "fit-first" layout. On
    // taller monitors the normal spacious layout is retained. This is based on
    // logical available height, so Windows/macOS/Linux DPI scaling is respected.
    readonly property bool fitFirstDesktop: Screen.desktopAvailableHeight >= 900
                                             && Screen.desktopAvailableHeight < 1200
                                             && height >= 850

    readonly property int responsivePageMargin: veryNarrowWidth ? 10 : (compactWidth ? 16 : (fitFirstDesktop ? 18 : 24))
    readonly property int responsiveSectionSpacing: compactHeight ? 12 : (fitFirstDesktop ? 14 : 20)
    readonly property int responsiveCardPadding: compactHeight ? 14 : (fitFirstDesktop ? 15 : 18)
    readonly property int responsiveCardSpacing: compactHeight ? 10 : (fitFirstDesktop ? 11 : 14)
    readonly property int responsiveButtonHeight: compactHeight ? 34 : (fitFirstDesktop ? 36 : 38)
    readonly property int responsiveTopBarHeight: compactHeight ? 58 : (fitFirstDesktop ? 64 : 72)
    readonly property int responsiveNavBarHeight: compactHeight ? 46 : (fitFirstDesktop ? 48 : 54)
    readonly property int responsiveStickyHeaderHeight: compactHeight ? 60 : (fitFirstDesktop ? 66 : 76)

    // The current UI language changes wrapping and therefore implicitHeight.
    // A page scrollbar is only needed when the REAL translated content, after
    // responsive fitting, is still taller than its viewport.
    function needsPageScroll(contentHeight, viewportHeight) {
        return contentHeight > viewportHeight + 2
    }

    Material.theme: Material.Dark
    Material.accent: clrAccent
    Material.primary: clrPrimary

    color: clrBg

    // ── Tek Premium Pro Koyu/Neon Palet (Siberpunk & Glassmorphism) ─────
    readonly property color clrBg:         "#0B0D10" // grafito profundo
    readonly property color clrSidebar:    "#101318" // superficie de navegación
    readonly property color clrSidebarTop: "#151922" // cabecera elevada
    readonly property color clrCard:       "#14181D" // panel de trabajo
    readonly property color clrCardHover:  "#1A2027" // panel activo
    readonly property color clrCardBorder: "#2A3139" // separador técnico
    readonly property color clrBorderGlow: "#B8F36B" // lima de estado
    readonly property color clrInput:      "#0F1216" // campos
    readonly property color clrPrimary:    "#12161B"
    readonly property color clrAccent:     "#B8F36B" // lima principal
    readonly property color clrAccent2:    "#A78BFA" // violeta secundario
    readonly property color clrPurple:     "#D77AF4" // magenta auxiliar
    readonly property color clrSuccess:    "#62D6A0" // correcto
    readonly property color clrSuccessDim: "#2462D6A0"
    readonly property color clrWarn:       "#F5C15D" // aviso
    readonly property color clrWarnDim:    "#24F5C15D"
    readonly property color clrError:      "#FF6B7A" // error
    readonly property color clrTxt:        "#F4F7F5" // texto principal
    readonly property color clrTxt2:       "#AAB3AD" // texto secundario
    readonly property color clrTxtDim:     "#6F7972" // texto atenuado

    // Geriye uyumluluk aliasları (sinyal/bağlantı koruması için)
    readonly property color cardBg:    clrCard
    readonly property color inputBg:   clrInput
    readonly property color borderClr: clrCardBorder
    readonly property color txtMain:   clrTxt
    readonly property color txtSecond: clrTxt2
    readonly property color txtDim:    clrTxtDim
    readonly property color clrTxtMuted: clrTxtDim
    readonly property color accentClr: clrAccent
    readonly property color successClr:clrSuccess
    readonly property color warningClr:clrWarn
    readonly property color errorClr:  clrError

    // ── State & Navigasyon ────────────────────────────────────────────────
    property int    navIndex:        0 // 0: Dashboard, 1: Settings, 2: Logs, 3: Toolbox
    property bool   isTranslating:   false
    property string currentStage:    "idle"
    property string stageCustomName: ""
    property int    totalLines:      0
    property int    translatedLines: 0
    property real   successRate:     0.0
    property string outputPath:      ""
    property bool   statsVisible:    false
    // Result breakdown (audit 2026-10-18): a run with pending lines is shown
    // as a warning, never as "completed successfully".
    property string statsScope:      "translation"
    property int    unchangedLines:  0
    property int    pendingLines:    0
    property bool   statsPartial:    false

    // ── Evrensel Dil Adı ve Kodu Çözümleyici (Undefined Bugfix) ──────────
    function getLangText(modelData, model) {
        var n = ""
        var c = ""
        if (typeof model !== "undefined" && model && model.name !== undefined) {
            n = model.name
            c = model.code !== undefined ? model.code : ""
        } else if (typeof modelData !== "undefined" && modelData) {
            if (modelData.name !== undefined) n = modelData.name
            else if (typeof modelData === "string") n = modelData
            if (modelData.code !== undefined) c = modelData.code
        }
        if (!n || n === "undefined") n = "Auto-detect"
        if (c && c !== "auto" && c !== "undefined") return n + " (" + c + ")"
        return n
    }

    // ── Catálogo visual en español para el selector de idiomas ─────────────
    // Solo afecta presentación/búsqueda; el backend sigue recibiendo los mismos códigos.
    readonly property var languageCatalogEs: ({
        "auto": { name: "Detectar automáticamente", iso: "AUTO" },
        "turkish": { name: "Turco", iso: "TR" },
        "english": { name: "Inglés", iso: "EN" },
        "german": { name: "Alemán", iso: "DE" },
        "french": { name: "Francés", iso: "FR" },
        "spanish": { name: "Español", iso: "ES" },
        "italian": { name: "Italiano", iso: "IT" },
        "portuguese": { name: "Portugués", iso: "PT" },
        "russian": { name: "Ruso", iso: "RU" },
        "polish": { name: "Polaco", iso: "PL" },
        "dutch": { name: "Neerlandés", iso: "NL" },
        "japanese": { name: "Japonés", iso: "JA" },
        "korean": { name: "Coreano", iso: "KO" },
        "chinese_s": { name: "Chino simplificado", iso: "ZH-CN" },
        "chinese_t": { name: "Chino tradicional", iso: "ZH-TW" },
        "arabic": { name: "Árabe", iso: "AR" },
        "thai": { name: "Tailandés", iso: "TH" },
        "vietnamese": { name: "Vietnamita", iso: "VI" },
        "indonesian": { name: "Indonesio", iso: "ID" },
        "malay": { name: "Malayo", iso: "MS" },
        "hindi": { name: "Hindi", iso: "HI" },
        "persian": { name: "Persa (farsi)", iso: "FA" },
        "czech": { name: "Checo", iso: "CS" },
        "danish": { name: "Danés", iso: "DA" },
        "finnish": { name: "Finés", iso: "FI" },
        "greek": { name: "Griego", iso: "EL" },
        "hebrew": { name: "Hebreo", iso: "HE" },
        "hungarian": { name: "Húngaro", iso: "HU" },
        "norwegian": { name: "Noruego", iso: "NO" },
        "romanian": { name: "Rumano", iso: "RO" },
        "swedish": { name: "Sueco", iso: "SV" },
        "ukrainian": { name: "Ucraniano", iso: "UK" },
        "bulgarian": { name: "Búlgaro", iso: "BG" },
        "catalan": { name: "Catalán", iso: "CA" },
        "croatian": { name: "Croata", iso: "HR" },
        "slovak": { name: "Eslovaco", iso: "SK" },
        "slovenian": { name: "Esloveno", iso: "SL" },
        "serbian": { name: "Serbio", iso: "SR" },
        "afrikaans": { name: "Afrikáans", iso: "AF" },
        "albanian": { name: "Albanés", iso: "SQ" },
        "amharic": { name: "Amárico", iso: "AM" },
        "armenian": { name: "Armenio", iso: "HY" },
        "azerbaijani": { name: "Azerbaiyano", iso: "AZ" },
        "basque": { name: "Vasco", iso: "EU" },
        "belarusian": { name: "Bielorruso", iso: "BE" },
        "bengali": { name: "Bengalí", iso: "BN" },
        "bosnian": { name: "Bosnio", iso: "BS" },
        "esperanto": { name: "Esperanto", iso: "EO" },
        "estonian": { name: "Estonio", iso: "ET" },
        "filipino": { name: "Filipino", iso: "TL" },
        "galician": { name: "Gallego", iso: "GL" },
        "georgian": { name: "Georgiano", iso: "KA" },
        "gujarati": { name: "Guyaratí", iso: "GU" },
        "haitian_creole": { name: "Criollo haitiano", iso: "HT" },
        "hausa": { name: "Hausa", iso: "HA" },
        "icelandic": { name: "Islandés", iso: "IS" },
        "igbo": { name: "Igbo", iso: "IG" },
        "irish": { name: "Irlandés", iso: "GA" },
        "javanese": { name: "Javanés", iso: "JV" },
        "kannada": { name: "Canarés (kannada)", iso: "KN" },
        "kazakh": { name: "Kazajo", iso: "KK" },
        "khmer": { name: "Jemer", iso: "KM" },
        "kurdish": { name: "Kurdo", iso: "KU" },
        "kyrgyz": { name: "Kirguís", iso: "KY" },
        "lao": { name: "Lao", iso: "LO" },
        "latvian": { name: "Letón", iso: "LV" },
        "lithuanian": { name: "Lituano", iso: "LT" },
        "luxembourgish": { name: "Luxemburgués", iso: "LB" },
        "macedonian": { name: "Macedonio", iso: "MK" },
        "malagasy": { name: "Malgache", iso: "MG" },
        "malayalam": { name: "Malayalam", iso: "ML" },
        "maltese": { name: "Maltés", iso: "MT" },
        "maori": { name: "Maorí", iso: "MI" },
        "marathi": { name: "Maratí", iso: "MR" },
        "mongolian": { name: "Mongol", iso: "MN" },
        "myanmar": { name: "Birmano", iso: "MY" },
        "nepali": { name: "Nepalí", iso: "NE" },
        "pashto": { name: "Pastún", iso: "PS" },
        "punjabi": { name: "Punyabí", iso: "PA" },
        "samoan": { name: "Samoano", iso: "SM" },
        "scots_gaelic": { name: "Gaélico escocés", iso: "GD" },
        "shona": { name: "Shona", iso: "SN" },
        "sindhi": { name: "Sindi", iso: "SD" },
        "sinhala": { name: "Cingalés", iso: "SI" },
        "somali": { name: "Somalí", iso: "SO" },
        "swahili": { name: "Suajili", iso: "SW" },
        "tajik": { name: "Tayiko", iso: "TG" },
        "tamil": { name: "Tamil", iso: "TA" },
        "telugu": { name: "Telugu", iso: "TE" },
        "urdu": { name: "Urdu", iso: "UR" },
        "uzbek": { name: "Uzbeko", iso: "UZ" },
        "welsh": { name: "Galés", iso: "CY" },
        "xhosa": { name: "Xhosa", iso: "XH" },
        "yiddish": { name: "Yidis", iso: "YI" },
        "yoruba": { name: "Yoruba", iso: "YO" },
        "zulu": { name: "Zulú", iso: "ZU" },
        "assamese": { name: "Asamés", iso: "AS" },
        "aymara": { name: "Aimara", iso: "AY" },
        "bambara": { name: "Bambara", iso: "BM" },
        "bhojpuri": { name: "Bhojpuri", iso: "BHO" },
        "cebuano": { name: "Cebuano", iso: "CEB" },
        "chichewa": { name: "Chichewa", iso: "NY" },
        "corsican": { name: "Corso", iso: "CO" },
        "dhivehi": { name: "Divehi", iso: "DV" },
        "dogri": { name: "Dogri", iso: "DOI" },
        "ewe": { name: "Ewé", iso: "EE" },
        "frisian": { name: "Frisón", iso: "FY" },
        "guarani": { name: "Guaraní", iso: "GN" },
        "hawaiian": { name: "Hawaiano", iso: "HAW" },
        "hmong": { name: "Hmong", iso: "HMN" },
        "ilocano": { name: "Ilocano", iso: "ILO" },
        "kinyarwanda": { name: "Kinyarwanda", iso: "RW" },
        "konkani": { name: "Konkani", iso: "GOM" },
        "krio": { name: "Krio", iso: "KRI" },
        "kurdish_sorani": { name: "Kurdo soraní", iso: "CKB" },
        "latin": { name: "Latín", iso: "LA" },
        "lingala": { name: "Lingala", iso: "LN" },
        "luganda": { name: "Luganda", iso: "LG" },
        "maithili": { name: "Maithili", iso: "MAI" },
        "meiteilon": { name: "Meitei (manipurí)", iso: "MNI-MTEI" },
        "mizo": { name: "Mizo", iso: "LUS" },
        "odia": { name: "Odia (oriya)", iso: "OR" },
        "oromo": { name: "Oromo", iso: "OM" },
        "quechua": { name: "Quechua", iso: "QU" },
        "sanskrit": { name: "Sánscrito", iso: "SA" },
        "sepedi": { name: "Sepedi (sotho del norte)", iso: "NSO" },
        "tatar": { name: "Tártaro", iso: "TT" },
        "tigrinya": { name: "Tigriña", iso: "TI" },
        "tsonga": { name: "Tsonga", iso: "TS" },
        "turkmen": { name: "Turcomano", iso: "TK" },
        "twi": { name: "Twi (akan)", iso: "AK" },
        "uyghur": { name: "Uigur", iso: "UG" },
        "crimean_tatar": { name: "Tártaro de Crimea", iso: "CRH" },
        "occitan": { name: "Occitano", iso: "OC" },
        "silesian": { name: "Silesio", iso: "SZL" },
        "tuvan": { name: "Tuvano", iso: "TYV" },
    })

    function spanishLanguageName(code, fallbackName) {
        // Conservado para compatibilidad y metadatos ISO. El nombre visible
        // se obtiene del idioma activo de la interfaz.
        var meta = languageCatalogEs[code]
        if (meta && meta.name) return meta.name
        if (fallbackName && fallbackName !== "undefined") return fallbackName
        return code || "Language"
    }

    function languageIsoCode(code) {
        var meta = languageCatalogEs[code]
        if (meta && meta.iso) return meta.iso
        return (code || "").toUpperCase()
    }

    function languageNativeName(fallbackName, code) {
        if (code === "auto") return ""
        var raw = fallbackName || ""
        var p = raw.lastIndexOf(" (")
        if (p > 0) raw = raw.substring(0, p)
        return raw.replace(/^\s+|\s+$/g, "")
    }

    function displayLanguageName(code, fallbackName) {
        var refresh = appBackend.uiTrigger
        if (code === "auto")
            return appBackend.getTextWithDefault("auto_detect", "Auto-detect")
        var nativeName = languageNativeName(fallbackName, code)
        return appBackend.getTextWithDefault("language_names." + code,
                                             nativeName || fallbackName || code || "Language")
    }

    function languageSecondaryName(fallbackName, code) {
        if (code === "auto") return ""
        var nativeName = languageNativeName(fallbackName, code)
        var primaryName = displayLanguageName(code, fallbackName)
        if (normalizeLanguageSearch(nativeName) === normalizeLanguageSearch(primaryName)) return ""
        return nativeName
    }

    function normalizeLanguageSearch(value) {
        var s = (value || "").toString().toLowerCase()
        s = s.replace(/[áàäâãå]/g, "a")
             .replace(/[éèëê]/g, "e")
             .replace(/[íìïî]/g, "i")
             .replace(/[óòöôõ]/g, "o")
             .replace(/[úùüû]/g, "u")
             .replace(/ñ/g, "n")
             .replace(/ç/g, "c")
        return s
    }

    function languageMatchesUISearch(item, query) {
        if (!item) return false
        var q = normalizeLanguageSearch(query).replace(/^\s+|\s+$/g, "")
        if (!q) return true
        var code = item.code || ""
        var nativeName = languageNativeName(item.name || "", code)
        var haystack = displayLanguageName(code, item.name || "") + " " + nativeName + " " +
                       (item.name || "") + " " + code + " " + languageIsoCode(code)
        return normalizeLanguageSearch(haystack).indexOf(q) !== -1
    }

    // ── Localized workspace names ────────────────────────────────────────────
    function workspaceTitle(index) {
        var refresh = appBackend.uiTrigger
        if (index === 0) return appBackend.getTextWithDefault("ln_header_translate", "Translation").toUpperCase()
        if (index === 1) return appBackend.getTextWithDefault("ln_header_config", "Configuration").toUpperCase()
        if (index === 2) return appBackend.getTextWithDefault("ln_header_diagnostics", "Diagnostics").toUpperCase()
        if (index === 3) return appBackend.getTextWithDefault("ln_header_tools", "Utilities").toUpperCase()
        if (index === 4) return appBackend.getTextWithDefault("ln_header_glossary", "Glossary").toUpperCase()
        if (index === 5) return appBackend.getTextWithDefault("ln_header_review", "Review").toUpperCase()
        if (index === 6) return appBackend.getTextWithDefault("mod_header_title", "MOD").toUpperCase()
        return "LINGUANOVA"
    }

    function workspaceHint(index) {
        var refresh = appBackend.uiTrigger
        if (index === 0) return appBackend.getTextWithDefault("ln_header_translate_hint", "Prepare the game, define the language route, and run the process.")
        if (index === 1) return appBackend.getTextWithDefault("ln_header_config_hint", "Control behavior, engines, output, network, and performance.")
        if (index === 2) return appBackend.getTextWithDefault("ln_header_diagnostics_hint", "See what is happening inside the process without hiding errors.")
        if (index === 3) return appBackend.getTextWithDefault("ln_header_tools_hint", "Auxiliary tools to adapt, check, and repair Ren'Py projects.")
        if (index === 4) return appBackend.getTextWithDefault("ln_header_glossary_hint", "Manage terms that must keep a consistent translation.")
        if (index === 5) return appBackend.getTextWithDefault("ln_header_review_hint", "Inspect and correct the result before considering it finished.")
        if (index === 6) return appBackend.getTextWithDefault(
            "mod_header_hint",
            "Choose a Ren'Py game, inspect its interface text and create an independent interface translation MOD.")
        return ""
    }

    // ── Başlangıç ─────────────────────────────────────────────────────────
    Component.onCompleted: {
        // La ruta del juego nunca se restaura entre sesiones.
        projectPathField.text = ""

        if (targetLangCombo && targetLangCombo.syncTargetLanguage) targetLangCombo.syncTargetLanguage()
        if (sourceLangCombo && sourceLangCombo.syncSourceLanguage) sourceLangCombo.syncSourceLanguage()
        if (uiLanguageCombo && uiLanguageCombo.syncUILanguage) uiLanguageCombo.syncUILanguage()

        appBackend.checkForUpdates(false)
    }

    // ── Backend Sinyalleri ────────────────────────────────────────────────
    Connections {
        target: appBackend

        function onLogMessage(level, message) {
            appendLog(level, message)
            if (message.indexOf("❌") >= 0 && (message.indexOf("select a game") >= 0 || message.indexOf("not found") >= 0 || message.indexOf("game folder") >= 0 || message.indexOf("oyun") >= 0))
                projectPathField.triggerShake()
            // Show toast for toolbox operations and key events
            if (message.indexOf("✅") === 0 && (message.indexOf("Font") >= 0 || message.indexOf("Lint") >= 0 || message.indexOf("terms") >= 0 || message.indexOf("imported") >= 0 || message.indexOf("exported") >= 0 || message.indexOf("filled") >= 0 || message.indexOf("translated") >= 0))
                showToast(message.replace("✅ ", ""), "success")
            else if (message.indexOf("⚠️") === 0 && (message.indexOf("failed") >= 0 || message.indexOf("not found") >= 0))
                showToast(message.replace("⚠️ ", ""), "warning")
            else if (message.indexOf("🔤") === 0 || message.indexOf("🩺") === 0 || message.indexOf("📚") === 0)
                showToast(message, "info")
        }

        function onProgressChanged(current, total, text) {
            if (total > 0) progressBar.value = current / total
            progressLabel.text = text + " (" + current + "/" + total + ")"
        }

        function onStageChanged(stage, displayName) {
            currentStage = stage
            stageCustomName = cleanStageText(displayName)
            var stageProgress = {
                "idle": 0, "validating": 5, "unren": 15,
                "generating": 30, "parsing": 40,
                "saving": 90, "completed": 100, "error": 0
            }
            if (stage !== "translating" && stageProgress[stage] !== undefined)
                progressBar.value = stageProgress[stage] / 100
        }

        function onTranslationStarted() {
            isTranslating = true
            // Close any route picker that happened to be open as the run started.
            if (sourceLangPopup.opened) sourceLangPopup.close()
            if (targetLangPopup.opened) targetLangPopup.close()
            statsVisible = false
            progressBar.value = 0
            progressLabel.text = ""
            currentStage = "starting"
            navIndex = 0 // Akışı anlık izlemek için Dashboard sekmene geç
        }

        function onTranslationFinished(success, message) {
            isTranslating = false
            if (success) {
                currentStage = "completed"
                progressBar.value = 1.0
                if (statsPartial)
                    showToast(appBackend.getTextWithDefault("translation_completed_partial", "Translation finished with pending lines"), "warning")
                else
                    showToast(appBackend.getTextWithDefault("translation_completed", "Çeviri tamamlandı!"), "success")
            } else {
                currentStage = "error"
                showToast(appBackend.getTextWithDefault("pipeline_translate_failed", "Translation failed") + ": " + message, "error")
            }
        }

        function onStatsReady(total, translated, untranslated) {
            // Banner numbers only; the backend logs the full breakdown
            // (translated / same as original / empty / failed / blocked).
            totalLines = total
            translatedLines = translated
            successRate = total > 0 ? (translated / total) * 100 : 0
        }

        function onStatsDetailReady(scope, total, translated, unchanged, pending, partial) {
            statsScope = scope
            totalLines = total
            translatedLines = translated
            unchangedLines = unchanged
            pendingLines = pending
            statsPartial = partial
            successRate = total > 0 ? (translated / total) * 100 : 0
            statsVisible = true
        }

        function onStatsCleared() {
            statsVisible = false
            statsPartial = false
            progressBar.value = 0
            progressLabel.text = ""
        }

        function onCompletionSummary(title, message, outPath, diagPath, reviewCount) {
            outputPath = outPath
            completionDialog.summaryText = message
            completionDialog.outputPath = outPath
            completionDialog.diagPath = diagPath
            completionDialog.open()
        }

        function onWarningMessage(title, message) {
            warningDialog.titleText = title
            warningDialog.bodyText = message
            warningDialog.open()
        }

        function onUpdateAvailable(currentVersion, latestVersion, releaseUrl) {
            updateDialog.latestVersion = latestVersion
            updateDialog.currentVersion = currentVersion
            updateDialog.releaseUrl = releaseUrl
            updateDialog.open()
        }

        function onUpdateCheckFinished(hasUpdate, message) {
            showToast(message, hasUpdate ? "success" : "info")
        }

        function onUpdateDownloadProgress(percent) {
            updateDialog.progress = percent
        }

        function onUpdateDownloadFinished(ok, message) {
            updateDialog.statusText = message
            // On failure the button falls back to opening the release page.
            if (!ok) updateDialog.autoFailed = true
        }

        function onUpdateInstallerLaunched() {
            // The installer replaces LinguaNova's files: close now so it can.
            Qt.quit()
        }
    }

    // ── Yardımcı Log Fonksiyonları ────────────────────────────────────────
    ListModel { id: logModel }

    function appendLog(level, message) {
        var ts = new Date().toLocaleTimeString(Qt.locale(), "HH:mm:ss")
        logModel.append({ "level": level, "message": message, "ts": ts })
        logListView.positionViewAtEnd()
        logConsoleListView.positionViewAtEnd()
    }

    Connections {
        target: editorBackend
        function onNotify(level, message) {
            appendLog(level, message)
            showToast(message, level)
        }
    }

    property bool editorCloseConfirmed: false
    onClosing: function(close) {
        // Text typed into the editor but not applied yet counts as unsaved too.
        if (!editorCloseConfirmed) pageEditor.commitPending()
        if (!editorCloseConfirmed && editorBackend.hasUnsavedChanges) {
            close.accepted = false
            editorCloseDialog.open()
        }
    }

    Dialog {
        id: editorCloseDialog
        parent: Overlay.overlay
        anchors.centerIn: parent
        modal: true
        title: appBackend.uiTrigger, appBackend.getTextWithDefault("editor_unsaved_title", "Unsaved changes")
        Label {
            text: appBackend.uiTrigger, appBackend.getTextWithDefault("editor_unsaved_close", "The editor has unsaved edits. Quit without saving?")
            color: clrTxt; wrapMode: Text.WordWrap
        }
        footer: DialogButtonBox {
            Button {
                text: appBackend.uiTrigger, appBackend.getTextWithDefault("editor_go_to_editor", "Go to editor")
                DialogButtonBox.buttonRole: DialogButtonBox.RejectRole
                onClicked: { editorCloseDialog.close(); navIndex = 5 }
            }
            Button {
                text: appBackend.uiTrigger, appBackend.getTextWithDefault("editor_quit_discard", "Quit without saving")
                DialogButtonBox.buttonRole: DialogButtonBox.DestructiveRole
                onClicked: { editorCloseConfirmed = true; editorCloseDialog.close(); root.close() }
            }
        }
    }

    function showToast(msg, type) {
        toast.show(msg, type)
    }

    function logColor(level) {
        if (level === "error")   return clrError
        if (level === "warning") return clrWarn
        if (level === "success") return clrSuccess
        if (level === "debug")   return clrTxtDim
        return clrTxt
    }

    function logPrefix(level) {
        var trigger = appBackend.uiTrigger
        if (level === "error")   return "[" + appBackend.getTextWithDefault("log_tag_error", "HATA").replace("[","").replace("]","") + "] "
        if (level === "warning") return "[" + appBackend.getTextWithDefault("log_tag_warn", "UYARI").replace("[","").replace("]","") + "] "
        if (level === "success") return "[" + appBackend.getTextWithDefault("log_tag_ok", "TAMAM").replace("[","").replace("]","") + "] "
        return "[" + appBackend.getTextWithDefault("log_tag_info", "BİLGİ").replace("[","").replace("]","") + "] "
    }

    function cleanModalTitle(str) {
        if (!str) return ""
        return str.replace(/^[\uD800-\uDBFF][\uDC00-\uDFFF]\s*/, "").replace(/^[🎉🚀✅⚠️📖➕]\s*/, "").trim()
    }

    function cleanStageText(str) {
        if (!str) return ""
        return str.replace(/[\.\s…]+$/, "").trim()
    }

    function getStageDisplayText(stage) {
        var trigger = appBackend.uiTrigger
        if (stage === "idle")
            return appBackend.getTextWithDefault("status_ready", "Ready - Waiting to Start")
        if (stage === "starting")
            return cleanStageText(appBackend.getTextWithDefault("starting_translation", "Starting translation..."))
        if (stage === "validating")
            return cleanStageText(appBackend.getTextWithDefault("stage_validating", "Validating..."))
        if (stage === "unren" || stage === "unrpa")
            return cleanStageText(appBackend.getTextWithDefault("stage_unren", "Decompiling (UnRen)..."))
        if (stage === "generating")
            return cleanStageText(appBackend.getTextWithDefault("stage_generating", "Generating Translation Files..."))
        if (stage === "parsing")
            return cleanStageText(appBackend.getTextWithDefault("stage_parsing", "Reading Files..."))
        if (stage === "translating")
            return cleanStageText(appBackend.getTextWithDefault("stage_translating", "Translating..."))
        if (stage === "saving")
            return cleanStageText(appBackend.getTextWithDefault("stage_saving", "Saving..."))
        if (stage === "completed")
            return cleanModalTitle(appBackend.getTextWithDefault("stage_completed", "Completed!")).replace("!", "") + " ✓"
        if (stage === "error")
            return cleanModalTitle(appBackend.getTextWithDefault("stage_error", "Error!"))
        return cleanStageText(stageCustomName.length > 0 ? stageCustomName : stage)
    }

    // ── Dosya ve Klasör Seçim Diyalogları ─────────────────────────────────
    FileDialog {
        id: fileDialog
        title: appBackend.uiTrigger, appBackend.getTextWithDefault("select_game_exe_title", "Oyun EXE Dosyasını Seç")
        nameFilters: Qt.platform.os === "windows"
            ? [appBackend.getTextWithDefault("renpy_games_filter", "Ren'Py Games") + " (*.exe)",
               appBackend.getTextWithDefault("all_files_filter", "All files") + " (*)"]
            : (Qt.platform.os === "osx" || Qt.platform.os === "macos")
            // Ren'Py's mac package is Game.app (game files in Contents/Resources/autorun)
            ? [appBackend.getTextWithDefault("renpy_games_filter", "Ren'Py Games") + " (*.app *.sh)",
               appBackend.getTextWithDefault("all_files_filter", "All files") + " (*)"]
            : [appBackend.getTextWithDefault("shell_scripts_filter", "Shell scripts") + " (*.sh)",
               appBackend.getTextWithDefault("all_files_filter", "All files") + " (*)"]
        onAccepted: {
            // A late native-dialog callback must never replace the active project.
            if (isTranslating) return
            var raw = selectedFile.toString()
            appBackend.setProjectPath(raw)
            projectPathField.text = appBackend.urlToPath(raw)
        }
    }

    FolderDialog {
        id: folderDialog
        title: appBackend.uiTrigger, appBackend.getTextWithDefault("select_game_folder_title", "Oyun Klasörünü Seç")
        onAccepted: {
            // The active translation owns its project path until it finishes.
            if (isTranslating) return
            var raw = selectedFolder.toString()
            appBackend.setProjectPath(raw)
            projectPathField.text = appBackend.urlToPath(raw)
        }
    }

    // #MOD — Selección independiente del juego. La ruta vive solo en memoria.
    FileDialog {
        id: modGameFileDialog
        title: appBackend.uiTrigger, appBackend.getTextWithDefault(
                   "mod_select_game_file_title", "Select the Ren'Py game file")
        nameFilters: Qt.platform.os === "windows"
            ? [appBackend.getTextWithDefault("renpy_games_filter", "Ren'Py Games") + " (*.exe)",
               appBackend.getTextWithDefault("all_files_filter", "All files") + " (*)"]
            : [appBackend.getTextWithDefault("all_files_filter", "All files") + " (*)"]
        onAccepted: {
            var raw = appBackend.urlToPath(selectedFile.toString())
            if (appBackend.setModProjectPath(raw))
                appBackend.analyzeMod()
        }
    }

    FolderDialog {
        id: modGameFolderDialog
        title: appBackend.uiTrigger, appBackend.getTextWithDefault(
                   "mod_select_game_folder_title", "Select the Ren'Py game folder")
        onAccepted: {
            var raw = appBackend.urlToPath(selectedFolder.toString())
            if (appBackend.setModProjectPath(raw))
                appBackend.analyzeMod()
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // LINGUANOVA WORKSPACE — cabecera + navegación horizontal
    // La antigua barra lateral fue eliminada deliberadamente para separar
    // visualmente esta aplicación de la interfaz de origen.
    // ═══════════════════════════════════════════════════════════════════════
    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: root.responsiveTopBarHeight
            color: clrBg

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: root.compactWidth ? 16 : 28
                anchors.rightMargin: root.compactWidth ? 16 : 28
                spacing: root.compactWidth ? 12 : 18

                Rectangle {
                    width: root.compactHeight ? 36 : 42
                    height: root.compactHeight ? 36 : 42
                    radius: 9
                    color: clrAccent
                    Label {
                        anchors.centerIn: parent
                        text: "LN"
                        color: "#0B0D10"
                        font.pixelSize: 14
                        font.bold: true
                        font.letterSpacing: 1.2
                    }
                }

                ColumnLayout {
                    spacing: 1
                    Label {
                        text: appBackend.uiTrigger, appBackend.getTextWithDefault("app_title", "LinguaNova")
                        color: clrTxt
                        font.pixelSize: 17
                        font.bold: true
                        font.letterSpacing: 0.7
                    }
                    Label {
                        text: (appBackend.uiTrigger, appBackend.getTextWithDefault("nav_workspace_label", "Ren'Py Translator").toUpperCase()) + "  /  v" + appBackend.version
                        color: clrTxtDim
                        font.pixelSize: 9
                        font.bold: true
                        font.letterSpacing: 1.4
                    }
                }

                Rectangle { width: 1; height: 34; color: clrCardBorder; Layout.leftMargin: 8; Layout.rightMargin: 8 }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2
                    Label {
                        text: workspaceTitle(navIndex)
                        color: clrAccent
                        font.pixelSize: 11
                        font.bold: true
                        font.letterSpacing: 1.8
                    }
                    Label {
                        text: workspaceHint(navIndex)
                        color: clrTxt2
                        font.pixelSize: root.compactHeight ? 11 : (root.fitFirstDesktop ? 11 : 12)
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                        visible: !root.narrowWidth
                    }
                }

                Rectangle {
                    implicitWidth: headerStatusRow.implicitWidth + 22
                    height: 34
                    radius: 6
                    color: isTranslating ? clrWarnDim : Qt.rgba(98, 214, 160, 0.10)
                    border.color: isTranslating ? clrWarn : Qt.rgba(98, 214, 160, 0.35)
                    border.width: 1
                    RowLayout {
                        id: headerStatusRow
                        anchors.centerIn: parent
                        spacing: 8
                        Rectangle { width: 7; height: 7; radius: 3.5; color: isTranslating ? clrWarn : clrSuccess }
                        Label {
                            text: appBackend.uiTrigger, (isTranslating ? appBackend.getTextWithDefault("ln_status_processing", "PROCESSING") : appBackend.getTextWithDefault("status_ready", "READY"))
                            color: isTranslating ? clrWarn : clrSuccess
                            font.pixelSize: 10
                            font.bold: true
                            font.letterSpacing: 1.1
                        }
                    }
                }
            }

            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: clrCardBorder }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: root.responsiveNavBarHeight
            color: clrSidebar

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: root.compactWidth ? 12 : 24
                anchors.rightMargin: root.compactWidth ? 12 : 24
                spacing: root.compactWidth ? 4 : 8

                Repeater {
                    model: ListModel {
                        // Navigation glyphs use permanent accent colors so MOD is not
                        // the only visually colored icon in the header.
                        ListElement { pageIndex: 0; navKey: "ln_header_translate"; navFallback: "Translate"; navGlyph: "▶"; navGlyphColor: "#B8F36B" }
                        ListElement { pageIndex: 4; navKey: "ln_header_glossary"; navFallback: "Glossary"; navGlyph: "A·Z"; navGlyphColor: "#D77AF4" }
                        ListElement { pageIndex: 5; navKey: "ln_header_review"; navFallback: "Review"; navGlyph: "✓"; navGlyphColor: "#62D6A0" }
                        // #MOD — Entrada principal independiente. No reutiliza el hook de traducción.
                        ListElement { pageIndex: 6; navKey: "nav_mod"; navFallback: "MOD"; navGlyph: "🧩"; navGlyphColor: "#B8F36B" }
                        ListElement { pageIndex: 1; navKey: "ln_header_config"; navFallback: "Configuration"; navGlyph: "≡"; navGlyphColor: "#A78BFA" }
                        ListElement { pageIndex: 2; navKey: "ln_header_diagnostics"; navFallback: "Diagnostics"; navGlyph: "⌁"; navGlyphColor: "#F5C15D" }
                        ListElement { pageIndex: 3; navKey: "ln_header_tools"; navFallback: "Utilities"; navGlyph: "+"; navGlyphColor: "#FF6B7A" }
                    }
                    delegate: Button {
                        required property int pageIndex
                        required property string navKey
                        // Freeze pages that could mutate the active translation. MOD is
                        // exempt because its requests are snapshot-based and join the FIFO queue.
                        enabled: !isTranslating || pageIndex === 6
                        required property string navFallback
                        required property string navGlyph
                        required property string navGlyphColor
                        // Keep navigation responsive without stretching every
                        // button across the row. Width follows the actual label.
                        Layout.fillWidth: false
                        Layout.minimumWidth: root.veryNarrowWidth ? 78 : 92
                        Layout.preferredWidth: Math.min(
                                                   root.compactWidth ? 138 : 176,
                                                   Math.max(
                                                       root.compactWidth ? 98 : 112,
                                                       navText.implicitWidth
                                                       + (navGlyph === "A·Z" ? 38 : 32)
                                                       + (root.compactWidth ? 18 : 24)
                                                   )
                                               )
                        Layout.maximumWidth: root.compactWidth ? 138 : 176
                        Layout.preferredHeight: root.compactHeight ? 36 : 38
                        onClicked: navIndex = pageIndex
                        background: Rectangle {
                            radius: 6
                            color: navIndex === pageIndex ? clrCard : (parent.hovered ? clrCardHover : "transparent")
                            border.color: navIndex === pageIndex ? clrAccent : "transparent"
                            border.width: 1
                            Rectangle {
                                anchors.bottom: parent.bottom
                                anchors.bottomMargin: 2
                                anchors.horizontalCenter: parent.horizontalCenter
                                width: navIndex === pageIndex ? parent.width - 20 : 0
                                height: 1
                                color: clrAccent
                                Behavior on width { NumberAnimation { duration: 150; easing.type: Easing.OutCubic } }
                            }
                        }
                        contentItem: RowLayout {
                            anchors.centerIn: parent
                            spacing: root.compactWidth ? 5 : 7
                            Label {
                                text: navGlyph
                                // Keep every navigation icon colored at all times.
                                // The MOD emoji keeps its native multicolor rendering.
                                color: navGlyphColor
                                opacity: enabled ? 1.0 : 0.55
                                font.pixelSize: navGlyph === "A·Z" ? 9 : 12
                                font.bold: true
                                Layout.alignment: Qt.AlignVCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                            Label {
                                id: navText
                                text: appBackend.uiTrigger, appBackend.getTextWithDefault(navKey, navFallback)
                                color: navIndex === pageIndex ? clrTxt : clrTxt2
                                font.pixelSize: root.compactWidth ? 11 : 12
                                font.bold: navIndex === pageIndex
                                Layout.maximumWidth: root.compactWidth ? 100 : 136
                                Layout.alignment: Qt.AlignVCenter
                                verticalAlignment: Text.AlignVCenter
                                elide: Text.ElideRight
                            }
                        }
                    }
                }

                Item { Layout.fillWidth: true }

                Button {
                    Layout.preferredWidth: root.veryNarrowWidth ? 66 : (root.compactWidth ? 78 : 92)
                    Layout.preferredHeight: root.compactHeight ? 30 : 34
                    onClicked: aboutDialog.open()
                    background: Rectangle {
                        radius: 6
                        color: parent.hovered ? clrCardHover : "transparent"
                        border.color: clrCardBorder
                        border.width: 1
                    }
                    contentItem: Label {
                        text: appBackend.uiTrigger, appBackend.getTextWithDefault("nav_about", "About")
                        color: clrTxt2
                        font.pixelSize: 11
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }

            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: clrCardBorder }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: navIndex

            // ═════════════════════════════════════════════════════════════
            // SEKME 0: DASHBOARD (Örnek Görseldeki Pro Kart Düzeni)
            // ═════════════════════════════════════════════════════════════
            Item {
                id: pageDashboard
                Layout.fillWidth: true
                Layout.fillHeight: true

                // ── SABİT STICKY HEADER (ASLA KAYBOLMAZ) ──────────────
                Rectangle {
                    id: dashStickyHeader
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    height: root.responsiveStickyHeaderHeight
                    color: clrBg
                    z: 10

                    RowLayout {
                        id: dashHeaderRow
                        anchors.fill: parent
                        anchors.leftMargin: root.compactWidth ? 18 : 36
                        anchors.rightMargin: root.compactWidth ? 18 : 36

                        transform: Translate { id: animTrDashHeader; y: 12 }
                        opacity: 0.0
                        SequentialAnimation {
                            id: animEntranceDashHeader
                            ParallelAnimation {
                                NumberAnimation { target: animTrDashHeader; property: "y"; to: 0; duration: 220; easing.type: Easing.OutCubic }
                                NumberAnimation { target: dashHeaderRow; property: "opacity"; to: 1.0; duration: 200; easing.type: Easing.OutQuad }
                            }
                        }
                        Component.onCompleted: if (navIndex === 0) animEntranceDashHeader.start()
                        Connections { target: root; function onNavIndexChanged() { if (navIndex === 0) animEntranceDashHeader.restart() } }

                        ColumnLayout {
                            spacing: 4
                            Label {
                                text: appBackend.uiTrigger, appBackend.getTextWithDefault("ln_workspace_translate_title", "Flujo de traducción")
                                font.pixelSize: 24; font.bold: true; color: clrTxt
                            }
                            Label {
                                text: appBackend.uiTrigger, appBackend.getTextWithDefault("ln_workspace_translate_desc", "Define el origen, el recorrido lingüístico y el motor. El núcleo conserva la estructura Ren'Py durante el proceso.")
                                font.pixelSize: 12; color: clrTxt2
                            }
                        }
                    }

                    // İnce ayrım çizgisi
                    Rectangle {
                        anchors.bottom: parent.bottom
                        anchors.left: parent.left; anchors.right: parent.right
                        height: 1
                        color: clrCardBorder
                        opacity: 0.6
                    }
                }

                // ── KAYDIRILABİLİR İÇERİK ALANI (RESPONSIVE MAX-WIDTH) ──
                ScrollView {
                    id: viewDashboard
                    anchors.top: dashStickyHeader.bottom
                    anchors.bottom: parent.bottom
                    anchors.left: parent.left
                    anchors.right: parent.right
                    clip: true
                    contentWidth: availableWidth
                    contentHeight: dashboardContent.implicitHeight
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                    ScrollBar.vertical.policy: root.needsPageScroll(viewDashboard.contentHeight, viewDashboard.availableHeight)
                                                   ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff

                    ColumnLayout {
                        id: dashboardContent
                        width: Math.max(0, Math.min(viewDashboard.availableWidth - (root.responsivePageMargin * 2), 1240))
                        anchors.horizontalCenter: parent.horizontalCenter
                        spacing: root.responsiveSectionSpacing

                        Item { height: 8 }

                    // ── KART 1: PROJECT SETUP (PROJE KURULUMU) ────────────
                    Rectangle {
                        id: cardProject
                        // Project selection stays immutable for the active pipeline.
                        enabled: !isTranslating
                        Layout.fillWidth: true
                        Layout.preferredHeight: projectInnerRow.implicitHeight + (root.compactHeight ? 30 : 44)
                        radius: 6; color: cardProject.hovered ? clrCardHover : clrCard
                        border.color: cardProject.hovered ? Qt.rgba(184, 243, 107, 0.4) : clrCardBorder
                        border.width: 1
                        property bool hovered: false
                        scale: 1.0
                        transformOrigin: Item.Center
                        Behavior on scale { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
                        Behavior on color { ColorAnimation { duration: 180 } }
                        Behavior on border.color { ColorAnimation { duration: 180 } }
                        HoverHandler { onHoveredChanged: cardProject.hovered = hovered }

                        // QW-1 Staggered Entrance
                        transform: Translate { id: animTrProject; y: 16 }
                        opacity: 0.0
                        SequentialAnimation {
                            id: animEntranceProject
                            PauseAnimation { duration: 0 }
                            ParallelAnimation {
                                NumberAnimation { target: animTrProject; property: "y"; to: 0; duration: 240; easing.type: Easing.OutCubic }
                                NumberAnimation { target: cardProject; property: "opacity"; to: 1.0; duration: 220; easing.type: Easing.OutQuad }
                            }
                        }
                        Component.onCompleted: if (navIndex === 0) animEntranceProject.start()
                        Connections { target: root; function onNavIndexChanged() { if (navIndex === 0) animEntranceProject.restart() } }

                        RowLayout {
                            id: projectInnerRow
                            anchors.fill: parent; anchors.margins: 22
                            spacing: 16

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 10

                                RowLayout {
                                    Layout.fillWidth: true
                                    Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("ln_project_source_title", "01  ORIGEN DEL PROYECTO"); font.pixelSize: 16; font.bold: true; color: clrTxt }
                                    Item { Layout.fillWidth: true }
                                    // Proje Durum Rozeti
                                    Rectangle {
                                        visible: projectPathField.text.length > 0
                                        height: 24
                                        Layout.preferredWidth: projBadgeRow.implicitWidth + 16
                                        radius: 6
                                        color: Qt.rgba(16, 185, 129, 0.15)
                                        border.color: Qt.rgba(16, 185, 129, 0.4)
                                        border.width: 1
                                        RowLayout {
                                            id: projBadgeRow
                                            anchors.centerIn: parent; spacing: 4
                                            Label { text: "✓"; color: clrSuccess; font.bold: true; font.pixelSize: 11 }
                                            Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("ln_project_ready", "ORIGEN CARGADO"); color: clrSuccess; font.pixelSize: 11; font.bold: true }
                                        }
                                    }
                                }

                                Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("ln_project_source_desc", "La ruta queda protegida contra edición manual. Cámbiala únicamente con uno de los selectores."); font.pixelSize: 12; color: clrTxt2 }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 12
                                    TextField {
                                        id: projectPathField
                                        Layout.fillWidth: true; height: 40
                                        font.pixelSize: 12; color: clrTxt
                                        // La ruta del juego es de solo lectura: se cambia únicamente
                                        // mediante los botones de selección de carpeta o EXE.
                                        readOnly: true
                                        selectByMouse: true
                                        property bool hasError: false
                                        onTextChanged: if (hasError) hasError = false

                                        transform: Translate { id: pathFieldShake; x: 0 }

                                        SequentialAnimation {
                                            id: shakeFieldAnim
                                            alwaysRunToEnd: true
                                            onStarted: projectPathField.hasError = true
                                            NumberAnimation { target: pathFieldShake; property: "x"; to: -8; duration: 40; easing.type: Easing.OutQuad }
                                            NumberAnimation { target: pathFieldShake; property: "x"; to: 8;  duration: 60; easing.type: Easing.InOutQuad }
                                            NumberAnimation { target: pathFieldShake; property: "x"; to: -6; duration: 50; easing.type: Easing.InOutQuad }
                                            NumberAnimation { target: pathFieldShake; property: "x"; to: 5;  duration: 45; easing.type: Easing.InOutQuad }
                                            NumberAnimation { target: pathFieldShake; property: "x"; to: 0;  duration: 40; easing.type: Easing.OutQuad }
                                            PauseAnimation { duration: 1200 }
                                            PropertyAction { target: projectPathField; property: "hasError"; value: false }
                                        }

                                        function triggerShake() {
                                            shakeFieldAnim.restart()
                                        }

                                        background: Rectangle {
                                            radius: 10
                                            color: clrInput
                                            border.color: projectPathField.hasError ? clrError : (projectPathField.activeFocus ? clrAccent : clrCardBorder)
                                            border.width: projectPathField.hasError ? 1.5 : 1
                                            Behavior on border.color { ColorAnimation { duration: 150 } }

                                            // QW-3 Focus Ring Glow & Error Halo (macOS/Fluent tarzı ışıma)
                                            Rectangle {
                                                anchors.fill: parent
                                                anchors.margins: -3
                                                radius: parent.radius + 2
                                                color: "transparent"
                                                border.color: projectPathField.hasError ? clrError : clrAccent
                                                border.width: 2
                                                opacity: projectPathField.hasError ? 0.65 : (projectPathField.activeFocus ? 0.35 : 0.0)
                                                scale: (projectPathField.hasError || projectPathField.activeFocus) ? 1.0 : 0.98
                                                Behavior on opacity { NumberAnimation { duration: 180; easing.type: Easing.OutQuad } }
                                                Behavior on scale { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
                                                Behavior on border.color { ColorAnimation { duration: 180 } }
                                            }
                                        }
                                        Label {
                                            anchors.left: parent.left; anchors.leftMargin: 12
                                            anchors.verticalCenter: parent.verticalCenter
                                            text: ""
                                            color: clrTxtDim; font.pixelSize: 12; visible: projectPathField.text.length === 0 && !projectPathField.activeFocus
                                        }
                                    }
                                    Button {
                                        id: btnBrowseFolder
                                        enabled: !isTranslating
                                        height: 42
                                        Layout.preferredWidth: Math.max(115, implicitContentWidth + 32)
                                        text: appBackend.uiTrigger, "▣ " + appBackend.getTextWithDefault("ln_pick_folder", "Ubicar carpeta")
                                        scale: down ? 0.96 : (hovered ? 1.03 : 1.0)
                                        transformOrigin: Item.Center
                                        Behavior on scale { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
                                        onClicked: folderDialog.open()
                                        background: Rectangle {
                                            radius: 12
                                            color: parent.down ? Qt.rgba(184, 243, 107, 0.1) : (parent.hovered ? clrCardHover : clrInput)
                                            border.color: parent.hovered ? Qt.rgba(184, 243, 107, 0.6) : clrCardBorder
                                            border.width: parent.hovered ? 1.5 : 1
                                            Behavior on color { ColorAnimation { duration: 150 } }
                                            Behavior on border.color { ColorAnimation { duration: 150 } }
                                        }
                                        contentItem: Label {
                                            text: parent.text; color: parent.hovered ? clrAccent : clrTxt
                                            font.pixelSize: 13; font.bold: true
                                            horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                                            Behavior on color { ColorAnimation { duration: 140 } }
                                        }
                                    }
                                    Button {
                                        id: btnBrowseExe
                                        enabled: !isTranslating
                                        height: 42
                                        Layout.preferredWidth: Math.max(135, implicitContentWidth + 32)
                                        text: appBackend.uiTrigger, "◆ " + appBackend.getTextWithDefault("ln_pick_exe", "Elegir ejecutable")
                                        scale: down ? 0.96 : (hovered ? 1.03 : 1.0)
                                        transformOrigin: Item.Center
                                        Behavior on scale { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
                                        onClicked: fileDialog.open()
                                        background: Rectangle {
                                            radius: 12
                                            color: parent.down ? Qt.rgba(184, 243, 107, 0.25) : (parent.hovered ? Qt.rgba(184, 243, 107, 0.15) : clrInput)
                                            border.color: parent.hovered ? clrAccent : Qt.rgba(184, 243, 107, 0.4)
                                            border.width: parent.hovered ? 1.5 : 1
                                            Behavior on color { ColorAnimation { duration: 150 } }
                                            Behavior on border.color { ColorAnimation { duration: 150 } }
                                        }
                                        contentItem: Label {
                                            text: parent.text; color: clrAccent
                                            font.pixelSize: 13; font.bold: true
                                            horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // ── KART 2: TRANSLATION ENGINE & LANGUAGES ────────────
                    Rectangle {
                        id: cardEngine
                        // Engine/source/target/model configuration is a run snapshot.
                        enabled: !isTranslating
                        Layout.fillWidth: true
                        property bool isAiEngine: appBackend.selectedEngine === "gemini" || appBackend.selectedEngine === "openai" || appBackend.selectedEngine === "deepseek"
                        Layout.preferredHeight: isAiEngine ? 228 : 135
                        clip: true
                        radius: 6; color: cardEngine.hovered ? clrCardHover : clrCard
                        border.color: cardEngine.hovered ? Qt.rgba(184, 243, 107, 0.4) : clrCardBorder
                        border.width: 1
                        property bool hovered: false
                        scale: 1.0
                        transformOrigin: Item.Center
                        Behavior on scale { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
                        Behavior on color { ColorAnimation { duration: 180 } }
                        Behavior on border.color { ColorAnimation { duration: 180 } }
                        Behavior on Layout.preferredHeight { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
                        HoverHandler { onHoveredChanged: cardEngine.hovered = hovered }

                        // QW-1 Staggered Entrance
                        transform: Translate { id: animTrEngine; y: 16 }
                        opacity: 0.0
                        SequentialAnimation {
                            id: animEntranceEngine
                            PauseAnimation { duration: 45 }
                            ParallelAnimation {
                                NumberAnimation { target: animTrEngine; property: "y"; to: 0; duration: 240; easing.type: Easing.OutCubic }
                                NumberAnimation { target: cardEngine; property: "opacity"; to: 1.0; duration: 220; easing.type: Easing.OutQuad }
                            }
                        }
                        Component.onCompleted: if (navIndex === 0) animEntranceEngine.start()
                        Connections { target: root; function onNavIndexChanged() { if (navIndex === 0) animEntranceEngine.restart() } }

                        ColumnLayout {
                            anchors.fill: parent; anchors.margins: 22
                            spacing: 14

                            RowLayout {
                                Layout.fillWidth: true
                                Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("ln_route_title", "02  RECORRIDO DE TRADUCCIÓN"); font.pixelSize: 16; font.bold: true; color: clrTxt }
                                Item { Layout.fillWidth: true }
                                Label {
                                    id: aiParamLink
                                    visible: cardEngine.isAiEngine
                                    text: appBackend.uiTrigger, appBackend.getTextWithDefault("ln_adjust_engine", "Engine settings  →")
                                    color: aiLinkMa.containsMouse ? "#FFFFFF" : clrAccent
                                    font.pixelSize: 12
                                    font.underline: true
                                    scale: aiLinkMa.pressed ? 0.96 : (aiLinkMa.containsMouse ? 1.04 : 1.0)
                                    Behavior on scale { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
                                    Behavior on color { ColorAnimation { duration: 140 } }
                                    MouseArea {
                                        id: aiLinkMa
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: navIndex = 1
                                    }
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 12

                                // ── Motor Seçimi ──────────────────────────────────────
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Layout.preferredWidth: 260
                                    Layout.minimumWidth: 200
                                    spacing: 5
                                    Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("ln_engine_label", "Motor que realizará la traducción"); font.pixelSize: 11; color: clrTxt2; font.bold: true }
                                    ComboBox {
                                        id: engineComboBox
                                        Layout.fillWidth: true; height: 40
                                        // Swapping engines mid-run would replace the translator the pipeline is using
                                        enabled: !isTranslating
                                        function engineModel() {
                                            appBackend.uiTrigger // Re-eval on language change
                                            return [
                                                {"id": "google", "name": "🌐 Google Translate (" + appBackend.getTextWithDefault("engine_desc_google", "Primary / Free") + ")"},
                                                {"id": "bing", "name": "🪟 Bing / Microsoft Edge (" + appBackend.getTextWithDefault("engine_desc_bing", "Free / No key") + ")"},
                                                {"id": "openai", "name": "🤖 OpenAI / GPT-4o (" + appBackend.getTextWithDefault("engine_desc_ai", "AI Engine") + ")"},
                                                {"id": "gemini", "name": "💎 Gemini (" + appBackend.getTextWithDefault("engine_desc_gemini", "Google AI") + ")"},
                                                {"id": "deepseek", "name": "🧠 DeepSeek AI (" + appBackend.getTextWithDefault("engine_desc_deepseek", "Fast / Economic") + ")"},
                                                {"id": "libretranslate", "name": "📖 LibreTranslate (" + appBackend.getTextWithDefault("engine_desc_local", "Self-hosted") + ")"}
                                            ]
                                        }
                                        model: engineModel()
                                        textRole: "name"; valueRole: "id"
                                        function syncIndex() {
                                            var idx = indexOfValue(appBackend.selectedEngine || "google");
                                            if (idx >= 0 && currentIndex !== idx) {
                                                currentIndex = idx;
                                            }
                                        }
                                        Component.onCompleted: syncIndex()
                                        Connections {
                                            target: appBackend
                                            function onSelectedEngineChanged(eng) { engineComboBox.syncIndex() }
                                            function onUiTriggerChanged() { engineComboBox.syncIndex() }
                                        }
                                        onActivated: { appBackend.setSelectedEngine(currentValue); appBackend.refreshUI() }
                                        background: Rectangle {
                                            radius: 10; color: clrInput; border.color: parent.hovered ? clrAccent : clrCardBorder; border.width: 1
                                            Behavior on border.color { ColorAnimation { duration: 150 } }
                                        }
                                        contentItem: Label { leftPadding: 14; text: engineComboBox.displayText; color: clrTxt; font.pixelSize: 12; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
                                        delegate: ItemDelegate {
                                            width: engineComboBox.width
                                            contentItem: Label { text: modelData.name; color: clrTxt; font.pixelSize: 12; leftPadding: 14; elide: Text.ElideRight }
                                            background: Rectangle { color: hovered ? Qt.rgba(184, 243, 107, 0.12) : "transparent"; Behavior on color { ColorAnimation { duration: 120 } } }
                                        }
                                        popup: Popup { y: engineComboBox.height + 4; width: engineComboBox.width; implicitHeight: Math.min(contentItem.implicitHeight, 240); padding: 4; contentItem: ListView { clip: true; implicitHeight: contentHeight; model: engineComboBox.delegateModel; ScrollBar.vertical: ScrollBar {} } background: Rectangle { color: clrCard; radius: 10; border.color: clrCardBorder; border.width: 1 } }
                                    }
                                }

                                // ── Kaynak Dil (2 Sütunlu Canlı Aranabilir Mega-Panel) ──
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Layout.preferredWidth: 320
                                    Layout.minimumWidth: 220
                                    spacing: 5

                                    RowLayout {
                                        Layout.fillWidth: true
                                        Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("ln_source_language", "Texto de origen"); font.pixelSize: 11; color: clrTxt2; font.bold: true; Layout.fillWidth: true }
                                        RowLayout {
                                            visible: false
                                            spacing: 4
                                            Repeater {
                                                model: [
                                                    { name: "Auto", code: "auto" },
                                                    { name: "JA", code: "japanese" },
                                                    { name: "EN", code: "english" },
                                                    { name: "ZH", code: "chinese_s" },
                                                    { name: "KO", code: "korean" }
                                                ]
                                                delegate: Rectangle {
                                                    height: 19; width: qkSrcTxt.implicitWidth + 10; radius: 4
                                                    color: sourceLangCombo.currentValue === modelData.code ? Qt.rgba(184, 243, 107, 0.22) : Qt.rgba(255, 255, 255, 0.05)
                                                    border.color: sourceLangCombo.currentValue === modelData.code ? clrAccent : Qt.rgba(255, 255, 255, 0.1)
                                                    border.width: 1
                                                    Label {
                                                        id: qkSrcTxt; anchors.centerIn: parent; text: modelData.name; font.pixelSize: 9; font.bold: true
                                                        color: sourceLangCombo.currentValue === modelData.code ? clrAccent : clrTxtDim
                                                    }
                                                    MouseArea {
                                                        anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                                        onClicked: { appBackend.setSourceLanguage(modelData.code); sourceLangCombo.syncSourceLanguage() }
                                                    }
                                                }
                                            }
                                        }
                                    }

                                    ComboBox {
                                        id: sourceLangCombo
                                        Layout.fillWidth: true; height: 40
                                        model: appBackend.getSourceLanguages()
                                        textRole: "name"; valueRole: "code"
                                        function syncSourceLanguage() {
                                            var src = appBackend.getSourceLanguage() || "auto"
                                            var idx = sourceLangCombo.indexOfValue(src)
                                            if (idx >= 0) sourceLangCombo.currentIndex = idx
                                        }
                                        Component.onCompleted: syncSourceLanguage()
                                        Connections {
                                            target: appBackend
                                            function onUiTriggerChanged() { sourceLangCombo.syncSourceLanguage() }
                                        }
                                        onActivated: appBackend.setSourceLanguage(currentValue)
                                        background: Rectangle {
                                            radius: 10; color: clrInput; border.color: parent.hovered ? clrAccent : clrCardBorder; border.width: 1
                                            Behavior on border.color { ColorAnimation { duration: 150 } }
                                        }
                                        contentItem: Label { leftPadding: 14; text: root.displayLanguageName(sourceLangCombo.currentValue, sourceLangCombo.displayText); color: clrTxt; font.pixelSize: 12; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
                                        delegate: ItemDelegate {
                                            width: sourceLangCombo.width
                                            contentItem: Label { text: root.displayLanguageName(modelData.code, modelData.name); color: sourceLangCombo.highlightedIndex === index ? clrAccent : clrTxt; font.pixelSize: 12; leftPadding: 14; elide: Text.ElideRight }
                                            background: Rectangle { color: hovered ? Qt.rgba(184, 243, 107, 0.12) : "transparent"; Behavior on color { ColorAnimation { duration: 120 } } }
                                        }
                                        popup: Popup {
                                            id: sourceLangPopup
                                            y: sourceLangCombo.height + 6
                                            width: Math.min(760, Math.max(430, root.width - 100))
                                            height: Math.min(468, Math.max(320, root.height - 210))
                                            padding: 12
                                            closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent

                                            property string searchFilter: ""
                                            property var allLanguages: []
                                            readonly property int columns: width >= 700 ? 4 : (width >= 520 ? 3 : 2)

                                            function refreshLanguages() {
                                                allLanguages = appBackend.getSourceLanguages() || []
                                            }

                                            function getFilteredList() {
                                                appBackend.uiTrigger
                                                var raw = allLanguages.length > 0 ? allLanguages : (appBackend.getSourceLanguages() || [])
                                                var res = []
                                                for (var i = 0; i < raw.length; i++) {
                                                    if (root.languageMatchesUISearch(raw[i], searchFilter)) res.push(raw[i])
                                                }
                                                return res
                                            }

                                            onAboutToShow: {
                                                refreshLanguages()
                                                searchFilter = ""
                                                sourceSearchInput.text = ""
                                                sourceSearchTimer.restart()
                                            }

                                            Timer {
                                                id: sourceSearchTimer
                                                interval: 70
                                                repeat: false
                                                onTriggered: sourceSearchInput.forceActiveFocus()
                                            }

                                            background: Rectangle {
                                                color: "#11161B"
                                                radius: 18
                                                border.color: "#313943"
                                                border.width: 1
                                            }

                                            contentItem: ColumnLayout {
                                                spacing: 10
                                                anchors.fill: parent

                                                // Cabecera propia: ya no imita el desplegable heredado.
                                                RowLayout {
                                                    Layout.fillWidth: true
                                                    spacing: 10
                                                    ColumnLayout {
                                                        Layout.fillWidth: true
                                                        spacing: 2
                                                        Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("ln_choose_source_language", "Choose source language"); color: clrTxt; font.pixelSize: 15; font.bold: true }
                                                        Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("ln_language_search_hint", "Search by language name, native name, or code."); color: clrTxtDim; font.pixelSize: 10 }
                                                    }
                                                    Button {
                                                        width: 28; height: 28
                                                        onClicked: sourceLangPopup.close()
                                                        background: Rectangle { radius: 8; color: parent.hovered ? "#252C34" : "#1A2026" }
                                                        contentItem: Label { text: "×"; color: clrTxt2; font.pixelSize: 18; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                                    }
                                                }

                                                // Búsqueda española real: acepta tildes, nombres nativos y códigos.
                                                Rectangle {
                                                    Layout.fillWidth: true; height: 42; radius: 12
                                                    color: "#0B0F13"
                                                    border.color: sourceSearchInput.activeFocus ? clrAccent2 : "#2C343D"
                                                    border.width: 1

                                                    RowLayout {
                                                        anchors.fill: parent; anchors.leftMargin: 12; anchors.rightMargin: 10; spacing: 8
                                                        Label { text: "⌕"; font.pixelSize: 18; color: sourceSearchInput.activeFocus ? clrAccent2 : clrTxtDim }
                                                        TextInput {
                                                            id: sourceSearchInput
                                                            Layout.fillWidth: true
                                                            font.pixelSize: 12; color: clrTxt
                                                            selectByMouse: true; clip: true
                                                            Text {
                                                                anchors.fill: parent; verticalAlignment: Text.AlignVCenter
                                                                text: appBackend.uiTrigger, appBackend.getTextWithDefault("ln_language_search_placeholder", "Search: German, Japanese, Chinese, es, ja...")
                                                                color: "#68737D"; font.pixelSize: 11
                                                                visible: !sourceSearchInput.text
                                                            }
                                                            onTextChanged: sourceLangPopup.searchFilter = text
                                                            onAccepted: {
                                                                var list = sourceLangPopup.getFilteredList()
                                                                if (list.length > 0) {
                                                                    appBackend.setSourceLanguage(list[0].code)
                                                                    sourceLangCombo.syncSourceLanguage()
                                                                    sourceLangPopup.close()
                                                                }
                                                            }
                                                        }
                                                        Button {
                                                            visible: sourceSearchInput.text.length > 0
                                                            width: 24; height: 24
                                                            onClicked: sourceSearchInput.text = ""
                                                            background: Rectangle { radius: 7; color: parent.hovered ? "#28313A" : "transparent" }
                                                            contentItem: Label { text: "×"; color: clrTxtDim; font.pixelSize: 15; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                                        }
                                                    }
                                                }

                                                // Mosaico adaptable: 4/3/2 columnas según el ancho disponible.
                                                GridView {
                                                    id: sourceMosaicGrid
                                                    Layout.fillWidth: true
                                                    Layout.fillHeight: true
                                                    clip: true
                                                    cellWidth: Math.floor(width / sourceLangPopup.columns)
                                                    cellHeight: 54
                                                    model: sourceLangPopup.getFilteredList()
                                                    boundsBehavior: Flickable.StopAtBounds
                                                    ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                                                    delegate: Item {
                                                        width: sourceMosaicGrid.cellWidth
                                                        height: sourceMosaicGrid.cellHeight

                                                        Rectangle {
                                                            anchors.fill: parent
                                                            anchors.margins: 3
                                                            radius: 11
                                                            color: sourceLangCombo.currentValue === modelData.code
                                                                   ? Qt.rgba(167/255, 139/255, 250/255, 0.13)
                                                                   : (sourceTileMouse.containsMouse ? "#1B2229" : "#151B21")
                                                            border.color: sourceLangCombo.currentValue === modelData.code ? clrAccent2 : "transparent"
                                                            border.width: sourceLangCombo.currentValue === modelData.code ? 1 : 0

                                                            RowLayout {
                                                                anchors.fill: parent
                                                                anchors.leftMargin: 9; anchors.rightMargin: 9
                                                                spacing: 8

                                                                Rectangle {
                                                                    width: 34; height: 30; radius: 8
                                                                    color: sourceLangCombo.currentValue === modelData.code ? clrAccent2 : "#222A32"
                                                                    Label {
                                                                        anchors.centerIn: parent
                                                                        text: root.languageIsoCode(modelData.code)
                                                                        color: sourceLangCombo.currentValue === modelData.code ? "#0B0D10" : "#9AA6B0"
                                                                        font.pixelSize: 8; font.bold: true
                                                                    }
                                                                }

                                                                ColumnLayout {
                                                                    Layout.fillWidth: true
                                                                    spacing: 0
                                                                    Label {
                                                                        Layout.fillWidth: true
                                                                        text: root.displayLanguageName(modelData.code, modelData.name)
                                                                        color: sourceLangCombo.currentValue === modelData.code ? clrAccent2 : clrTxt
                                                                        font.pixelSize: 10; font.bold: true
                                                                        elide: Text.ElideRight
                                                                    }
                                                                    Label {
                                                                        Layout.fillWidth: true
                                                                        visible: root.languageSecondaryName(modelData.name, modelData.code).length > 0
                                                                        text: root.languageSecondaryName(modelData.name, modelData.code)
                                                                        color: "#707B85"; font.pixelSize: 8
                                                                        elide: Text.ElideRight
                                                                    }
                                                                }

                                                                Label {
                                                                    visible: sourceLangCombo.currentValue === modelData.code
                                                                    text: "●"; color: clrAccent2; font.pixelSize: 9
                                                                }
                                                            }

                                                            MouseArea {
                                                                id: sourceTileMouse
                                                                anchors.fill: parent
                                                                hoverEnabled: true
                                                                cursorShape: Qt.PointingHandCursor
                                                                onClicked: {
                                                                    appBackend.setSourceLanguage(modelData.code)
                                                                    sourceLangCombo.syncSourceLanguage()
                                                                    sourceLangPopup.close()
                                                                }
                                                            }
                                                        }
                                                    }
                                                }

                                                RowLayout {
                                                    Layout.fillWidth: true
                                                    Label {
                                                        text: appBackend.uiTrigger, appBackend.getTextWithDefault("ln_languages_visible", "{count} languages visible").replace("{count}", sourceLangPopup.getFilteredList().length)
                                                        font.pixelSize: 9; color: "#6F7B85"
                                                    }
                                                    Item { Layout.fillWidth: true }
                                                    Label {
                                                        text: appBackend.uiTrigger, appBackend.getTextWithDefault("ln_language_picker_keys", "Enter: select  ·  Esc: close")
                                                        font.pixelSize: 9; color: "#6F7B85"
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }

                                // ── Dil Takas Butonu (Swap) ──────────────────────────
                                Button {
                                    id: btnSwapLanguages
                                    Layout.preferredWidth: 36
                                    Layout.preferredHeight: 36
                                    Layout.alignment: Qt.AlignBottom
                                    Layout.bottomMargin: 2
                                    ToolTip.visible: hovered
                                    ToolTip.text: appBackend.uiTrigger, appBackend.getTextWithDefault("ln_swap_languages", "Intercambiar origen y destino")
                                    ToolTip.delay: 250

                                    background: Rectangle {
                                        radius: 10
                                        color: btnSwapLanguages.hovered ? Qt.rgba(184, 243, 107, 0.15) : clrInput
                                        border.color: btnSwapLanguages.hovered ? clrAccent : clrCardBorder
                                        border.width: 1
                                        Behavior on color { ColorAnimation { duration: 120 } }
                                        Behavior on border.color { ColorAnimation { duration: 120 } }
                                    }

                                    contentItem: Label {
                                        text: "⇄"
                                        font.pixelSize: 16
                                        font.bold: true
                                        color: btnSwapLanguages.hovered ? "#FFFFFF" : clrAccent
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                        rotation: btnSwapLanguages.pressed ? 180 : 0
                                        Behavior on rotation { NumberAnimation { duration: 250; easing.type: Easing.OutBack } }
                                    }

                                    onClicked: {
                                        var curSrc = appBackend.getSourceLanguage() || "auto"
                                        var curTgt = appBackend.getTargetLanguage() || "turkish"
                                        if (curSrc === "auto") {
                                            appBackend.setSourceLanguage(curTgt)
                                            appBackend.setTargetLanguage(curTgt === "english" ? "turkish" : "english")
                                        } else {
                                            appBackend.setSourceLanguage(curTgt)
                                            appBackend.setTargetLanguage(curSrc)
                                        }
                                        sourceLangCombo.syncSourceLanguage()
                                        targetLangCombo.syncTargetLanguage()
                                    }
                                }

                                // ── Hedef Dil (2 Sütunlu Canlı Aranabilir Mega-Panel) ──
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Layout.preferredWidth: 320
                                    Layout.minimumWidth: 220
                                    spacing: 5

                                    RowLayout {
                                        Layout.fillWidth: true
                                        Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("ln_target_language", "Resultado deseado"); font.pixelSize: 11; color: clrTxt2; font.bold: true; Layout.fillWidth: true }
                                        RowLayout {
                                            visible: false
                                            spacing: 4
                                            Repeater {
                                                model: [
                                                    { name: "TR", code: "turkish" },
                                                    { name: "EN", code: "english" },
                                                    { name: "DE", code: "german" },
                                                    { name: "ES", code: "spanish" },
                                                    { name: "RU", code: "russian" },
                                                    { name: "FR", code: "french" }
                                                ]
                                                delegate: Rectangle {
                                                    height: 19; width: qkTgtTxt.implicitWidth + 10; radius: 4
                                                    color: targetLangCombo.currentValue === modelData.code ? Qt.rgba(184, 243, 107, 0.22) : Qt.rgba(255, 255, 255, 0.05)
                                                    border.color: targetLangCombo.currentValue === modelData.code ? clrAccent : Qt.rgba(255, 255, 255, 0.1)
                                                    border.width: 1
                                                    Label {
                                                        id: qkTgtTxt; anchors.centerIn: parent; text: modelData.name; font.pixelSize: 9; font.bold: true
                                                        color: targetLangCombo.currentValue === modelData.code ? clrAccent : clrTxtDim
                                                    }
                                                    MouseArea {
                                                        anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                                        onClicked: { appBackend.setTargetLanguage(modelData.code); targetLangCombo.syncTargetLanguage() }
                                                    }
                                                }
                                            }
                                        }
                                    }

                                    ComboBox {
                                        id: targetLangCombo
                                        Layout.fillWidth: true; height: 40
                                        model: appBackend.getTargetLanguages()
                                        textRole: "name"; valueRole: "code"
                                        function syncTargetLanguage() {
                                            var tgt = appBackend.getTargetLanguage() || "turkish"
                                            var idx = targetLangCombo.indexOfValue(tgt)
                                            if (idx >= 0) targetLangCombo.currentIndex = idx
                                        }
                                        Component.onCompleted: syncTargetLanguage()
                                        Connections {
                                            target: appBackend
                                            function onUiTriggerChanged() { targetLangCombo.syncTargetLanguage() }
                                        }
                                        onActivated: appBackend.setTargetLanguage(currentValue)
                                        background: Rectangle {
                                            radius: 10; color: clrInput; border.color: parent.hovered ? clrAccent : clrCardBorder; border.width: 1
                                            Behavior on border.color { ColorAnimation { duration: 150 } }
                                        }
                                        contentItem: Label { leftPadding: 14; text: root.displayLanguageName(targetLangCombo.currentValue, targetLangCombo.displayText); color: clrTxt; font.pixelSize: 12; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
                                        delegate: ItemDelegate {
                                            width: targetLangCombo.width
                                            contentItem: Label { text: root.displayLanguageName(modelData.code, modelData.name); color: targetLangCombo.highlightedIndex === index ? clrAccent : clrTxt; font.pixelSize: 12; leftPadding: 14; elide: Text.ElideRight }
                                            background: Rectangle { color: hovered ? Qt.rgba(184, 243, 107, 0.12) : "transparent"; Behavior on color { ColorAnimation { duration: 120 } } }
                                        }
                                        popup: Popup {
                                            id: targetLangPopup
                                            y: targetLangCombo.height + 6
                                            width: Math.min(760, Math.max(430, root.width - 100))
                                            height: Math.min(468, Math.max(320, root.height - 210))
                                            padding: 12
                                            closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent

                                            property string searchFilter: ""
                                            property var allLanguages: []
                                            readonly property int columns: width >= 700 ? 4 : (width >= 520 ? 3 : 2)

                                            function refreshLanguages() {
                                                allLanguages = appBackend.getTargetLanguages() || []
                                            }

                                            function getFilteredList() {
                                                appBackend.uiTrigger
                                                var raw = allLanguages.length > 0 ? allLanguages : (appBackend.getTargetLanguages() || [])
                                                var res = []
                                                for (var i = 0; i < raw.length; i++) {
                                                    if (root.languageMatchesUISearch(raw[i], searchFilter)) res.push(raw[i])
                                                }
                                                return res
                                            }

                                            onAboutToShow: {
                                                refreshLanguages()
                                                searchFilter = ""
                                                targetSearchInput.text = ""
                                                targetSearchTimer.restart()
                                            }

                                            Timer {
                                                id: targetSearchTimer
                                                interval: 70
                                                repeat: false
                                                onTriggered: targetSearchInput.forceActiveFocus()
                                            }

                                            background: Rectangle {
                                                color: "#11161B"
                                                radius: 18
                                                border.color: "#313943"
                                                border.width: 1
                                            }

                                            contentItem: ColumnLayout {
                                                spacing: 10
                                                anchors.fill: parent

                                                // Cabecera propia: ya no imita el desplegable heredado.
                                                RowLayout {
                                                    Layout.fillWidth: true
                                                    spacing: 10
                                                    ColumnLayout {
                                                        Layout.fillWidth: true
                                                        spacing: 2
                                                        Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("ln_choose_target_language", "Choose target language"); color: clrTxt; font.pixelSize: 15; font.bold: true }
                                                        Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("ln_language_search_hint", "Search by language name, native name, or code."); color: clrTxtDim; font.pixelSize: 10 }
                                                    }
                                                    Button {
                                                        width: 28; height: 28
                                                        onClicked: targetLangPopup.close()
                                                        background: Rectangle { radius: 8; color: parent.hovered ? "#252C34" : "#1A2026" }
                                                        contentItem: Label { text: "×"; color: clrTxt2; font.pixelSize: 18; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                                    }
                                                }

                                                // Búsqueda española real: acepta tildes, nombres nativos y códigos.
                                                Rectangle {
                                                    Layout.fillWidth: true; height: 42; radius: 12
                                                    color: "#0B0F13"
                                                    border.color: targetSearchInput.activeFocus ? clrAccent : "#2C343D"
                                                    border.width: 1

                                                    RowLayout {
                                                        anchors.fill: parent; anchors.leftMargin: 12; anchors.rightMargin: 10; spacing: 8
                                                        Label { text: "⌕"; font.pixelSize: 18; color: targetSearchInput.activeFocus ? clrAccent : clrTxtDim }
                                                        TextInput {
                                                            id: targetSearchInput
                                                            Layout.fillWidth: true
                                                            font.pixelSize: 12; color: clrTxt
                                                            selectByMouse: true; clip: true
                                                            Text {
                                                                anchors.fill: parent; verticalAlignment: Text.AlignVCenter
                                                                text: appBackend.uiTrigger, appBackend.getTextWithDefault("ln_language_search_placeholder", "Search: German, Japanese, Chinese, es, ja...")
                                                                color: "#68737D"; font.pixelSize: 11
                                                                visible: !targetSearchInput.text
                                                            }
                                                            onTextChanged: targetLangPopup.searchFilter = text
                                                            onAccepted: {
                                                                var list = targetLangPopup.getFilteredList()
                                                                if (list.length > 0) {
                                                                    appBackend.setTargetLanguage(list[0].code)
                                                                    targetLangCombo.syncTargetLanguage()
                                                                    targetLangPopup.close()
                                                                }
                                                            }
                                                        }
                                                        Button {
                                                            visible: targetSearchInput.text.length > 0
                                                            width: 24; height: 24
                                                            onClicked: targetSearchInput.text = ""
                                                            background: Rectangle { radius: 7; color: parent.hovered ? "#28313A" : "transparent" }
                                                            contentItem: Label { text: "×"; color: clrTxtDim; font.pixelSize: 15; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                                        }
                                                    }
                                                }

                                                // Mosaico adaptable: 4/3/2 columnas según el ancho disponible.
                                                GridView {
                                                    id: targetMosaicGrid
                                                    Layout.fillWidth: true
                                                    Layout.fillHeight: true
                                                    clip: true
                                                    cellWidth: Math.floor(width / targetLangPopup.columns)
                                                    cellHeight: 54
                                                    model: targetLangPopup.getFilteredList()
                                                    boundsBehavior: Flickable.StopAtBounds
                                                    ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                                                    delegate: Item {
                                                        width: targetMosaicGrid.cellWidth
                                                        height: targetMosaicGrid.cellHeight

                                                        Rectangle {
                                                            anchors.fill: parent
                                                            anchors.margins: 3
                                                            radius: 11
                                                            color: targetLangCombo.currentValue === modelData.code
                                                                   ? Qt.rgba(184/255, 243/255, 107/255, 0.13)
                                                                   : (targetTileMouse.containsMouse ? "#1B2229" : "#151B21")
                                                            border.color: targetLangCombo.currentValue === modelData.code ? clrAccent : "transparent"
                                                            border.width: targetLangCombo.currentValue === modelData.code ? 1 : 0

                                                            RowLayout {
                                                                anchors.fill: parent
                                                                anchors.leftMargin: 9; anchors.rightMargin: 9
                                                                spacing: 8

                                                                Rectangle {
                                                                    width: 34; height: 30; radius: 8
                                                                    color: targetLangCombo.currentValue === modelData.code ? clrAccent : "#222A32"
                                                                    Label {
                                                                        anchors.centerIn: parent
                                                                        text: root.languageIsoCode(modelData.code)
                                                                        color: targetLangCombo.currentValue === modelData.code ? "#0B0D10" : "#9AA6B0"
                                                                        font.pixelSize: 8; font.bold: true
                                                                    }
                                                                }

                                                                ColumnLayout {
                                                                    Layout.fillWidth: true
                                                                    spacing: 0
                                                                    Label {
                                                                        Layout.fillWidth: true
                                                                        text: root.displayLanguageName(modelData.code, modelData.name)
                                                                        color: targetLangCombo.currentValue === modelData.code ? clrAccent : clrTxt
                                                                        font.pixelSize: 10; font.bold: true
                                                                        elide: Text.ElideRight
                                                                    }
                                                                    Label {
                                                                        Layout.fillWidth: true
                                                                        visible: root.languageSecondaryName(modelData.name, modelData.code).length > 0
                                                                        text: root.languageSecondaryName(modelData.name, modelData.code)
                                                                        color: "#707B85"; font.pixelSize: 8
                                                                        elide: Text.ElideRight
                                                                    }
                                                                }

                                                                Label {
                                                                    visible: targetLangCombo.currentValue === modelData.code
                                                                    text: "●"; color: clrAccent; font.pixelSize: 9
                                                                }
                                                            }

                                                            MouseArea {
                                                                id: targetTileMouse
                                                                anchors.fill: parent
                                                                hoverEnabled: true
                                                                cursorShape: Qt.PointingHandCursor
                                                                onClicked: {
                                                                    appBackend.setTargetLanguage(modelData.code)
                                                                    targetLangCombo.syncTargetLanguage()
                                                                    targetLangPopup.close()
                                                                }
                                                            }
                                                        }
                                                    }
                                                }

                                                RowLayout {
                                                    Layout.fillWidth: true
                                                    Label {
                                                        text: appBackend.uiTrigger, appBackend.getTextWithDefault("ln_languages_visible", "{count} languages visible").replace("{count}", targetLangPopup.getFilteredList().length)
                                                        font.pixelSize: 9; color: "#6F7B85"
                                                    }
                                                    Item { Layout.fillWidth: true }
                                                    Label {
                                                        text: appBackend.uiTrigger, appBackend.getTextWithDefault("ln_language_picker_keys", "Enter: select  ·  Esc: close")
                                                        font.pixelSize: 9; color: "#6F7B85"
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }

                            // ── AI HIZLI YAPILANDIRMA BARI (Dashboard Quick Config) ──
                            Rectangle {
                                Layout.fillWidth: true
                                height: 1
                                color: clrCardBorder
                                opacity: 0.6
                                visible: cardEngine.isAiEngine
                            }

                            // 1) Gemini Hızlı Yapılandırma
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 14
                                visible: appBackend.selectedEngine === "gemini"

                                ColumnLayout {
                                    Layout.fillWidth: true; Layout.preferredWidth: 4; spacing: 4
                                    Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("label_gemini_key", "Gemini API Key:"); color: clrTxt2; font.pixelSize: 11; font.bold: true }
                                    TextField {
                                        id: quickGeminiKeyField
                                        Layout.fillWidth: true; height: 38
                                        text: appBackend.geminiApiKey; echoMode: TextInput.Password; placeholderText: "AIza..."
                                        onEditingFinished: appBackend.geminiApiKey = text
                                        background: Rectangle {
                                            radius: 10; color: clrInput; border.color: parent.activeFocus ? clrAccent : clrCardBorder; border.width: 1
                                            Behavior on border.color { ColorAnimation { duration: 150 } }
                                        }
                                    }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true; Layout.preferredWidth: 3; spacing: 4
                                    Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("label_gemini_model", "Model:"); color: clrTxt2; font.pixelSize: 11; font.bold: true }
                                    TextField {
                                        id: quickGeminiModelField
                                        Layout.fillWidth: true; height: 38
                                        text: appBackend.geminiModel; placeholderText: "gemini-2.0-flash"
                                        onEditingFinished: appBackend.geminiModel = text
                                        background: Rectangle {
                                            radius: 10; color: clrInput; border.color: parent.activeFocus ? clrAccent : clrCardBorder; border.width: 1
                                            Behavior on border.color { ColorAnimation { duration: 150 } }
                                        }
                                    }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true; Layout.preferredWidth: 4; spacing: 4
                                    Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("label_gemini_safety", "Safety Filter Level:"); color: clrTxt2; font.pixelSize: 11; font.bold: true }
                                    ComboBox {
                                        id: quickGeminiSafetyCombo
                                        Layout.fillWidth: true; height: 38
                                        function safetyModel() {
                                            appBackend.uiTrigger
                                            return [
                                                { "id": "BLOCK_NONE", "name": "BLOCK_NONE (NSFW / Free)" },
                                                { "id": "BLOCK_ONLY_HIGH", "name": "BLOCK_ONLY_HIGH (High Risk)" },
                                                { "id": "STANDARD", "name": "STANDARD (Strict)" }
                                            ]
                                        }
                                        model: safetyModel()
                                        textRole: "name"; valueRole: "id"
                                        function syncSafety() {
                                            var val = appBackend.geminiSafetySettings || "BLOCK_NONE"
                                            var idx = quickGeminiSafetyCombo.indexOfValue(val)
                                            if (idx >= 0) quickGeminiSafetyCombo.currentIndex = idx
                                        }
                                        Component.onCompleted: syncSafety()
                                        Connections {
                                            target: appBackend
                                            function onGeminiSafetySettingsChanged() { quickGeminiSafetyCombo.syncSafety() }
                                            function onUiTriggerChanged() { quickGeminiSafetyCombo.syncSafety() }
                                        }
                                        onActivated: appBackend.geminiSafetySettings = currentValue
                                        background: Rectangle {
                                            radius: 10; color: clrInput; border.color: parent.hovered ? clrAccent : clrCardBorder; border.width: 1
                                            Behavior on border.color { ColorAnimation { duration: 150 } }
                                        }
                                        contentItem: Label { leftPadding: 12; text: quickGeminiSafetyCombo.displayText; color: clrTxt; font.pixelSize: 11; verticalAlignment: Text.AlignVCenter }
                                        delegate: ItemDelegate {
                                            width: quickGeminiSafetyCombo.width
                                            contentItem: Label { text: modelData.name; color: clrTxt; font.pixelSize: 11; leftPadding: 12 }
                                            background: Rectangle { color: hovered ? Qt.rgba(184, 243, 107, 0.12) : "transparent"; Behavior on color { ColorAnimation { duration: 120 } } }
                                        }
                                        popup: Popup { y: quickGeminiSafetyCombo.height; width: quickGeminiSafetyCombo.width; implicitHeight: Math.min(contentItem.implicitHeight, 180); padding: 4; contentItem: ListView { clip: true; implicitHeight: contentHeight; model: quickGeminiSafetyCombo.delegateModel; ScrollBar.vertical: ScrollBar {} } background: Rectangle { color: clrCard; radius: 10; border.color: clrCardBorder; border.width: 1 } }
                                    }
                                }
                            }

                            // 2) OpenAI / DeepSeek Hızlı Yapılandırma
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 14
                                visible: appBackend.selectedEngine === "openai" || appBackend.selectedEngine === "deepseek"

                                ColumnLayout {
                                    Layout.fillWidth: true; Layout.preferredWidth: 6; spacing: 4
                                    Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("label_openai_key", "API Key:"); color: clrTxt2; font.pixelSize: 11; font.bold: true }
                                    TextField {
                                        id: quickOpenaiKeyField
                                        Layout.fillWidth: true; height: 38
                                        text: appBackend.openaiApiKey; echoMode: TextInput.Password; placeholderText: "sk-..."
                                        onEditingFinished: appBackend.openaiApiKey = text
                                        background: Rectangle {
                                            radius: 10; color: clrInput; border.color: parent.activeFocus ? clrAccent : clrCardBorder; border.width: 1
                                            Behavior on border.color { ColorAnimation { duration: 150 } }
                                        }
                                    }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true; Layout.preferredWidth: 5; spacing: 4
                                    Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("label_openai_model", "Model:"); color: clrTxt2; font.pixelSize: 11; font.bold: true }
                                    TextField {
                                        id: quickOpenaiModelField
                                        Layout.fillWidth: true; height: 38
                                        text: appBackend.openaiModel; placeholderText: appBackend.selectedEngine === "deepseek" ? "deepseek-chat" : "gpt-4o-mini"
                                        onEditingFinished: appBackend.openaiModel = text
                                        background: Rectangle {
                                            radius: 10; color: clrInput; border.color: parent.activeFocus ? clrAccent : clrCardBorder; border.width: 1
                                            Behavior on border.color { ColorAnimation { duration: 150 } }
                                        }
                                    }
                                }
                            }



                            // Senkronizasyon Bağlantıları (Settings sekmesiyle anlık iki-yönlü parite)
                            Connections {
                                target: appBackend
                                function onGeminiApiKeyChanged() { quickGeminiKeyField.text = appBackend.geminiApiKey }
                                function onGeminiModelChanged() { quickGeminiModelField.text = appBackend.geminiModel }
                                function onOpenaiApiKeyChanged() { quickOpenaiKeyField.text = appBackend.openaiApiKey }
                                function onOpenaiModelChanged() { quickOpenaiModelField.text = appBackend.openaiModel }
                            }
                        }
                    }

                    // ── ANA AKSİYON BUTONU (NEON CYAN -> BLUE GRADIENT) ───
                    Button {
                        id: startButton
                        Layout.fillWidth: true
                        Layout.preferredHeight: 52
                        enabled: !isTranslating || currentStage !== "idle"

                        // QW-1 Staggered Entrance
                        transform: Translate { id: animTrStart; y: 16 }
                        opacity: 0.0
                        SequentialAnimation {
                            id: animEntranceStart
                            PauseAnimation { duration: 90 }
                            ParallelAnimation {
                                NumberAnimation { target: animTrStart; property: "y"; to: 0; duration: 240; easing.type: Easing.OutCubic }
                                NumberAnimation { target: startButton; property: "opacity"; to: 1.0; duration: 220; easing.type: Easing.OutQuad }
                            }
                        }
                        Component.onCompleted: if (navIndex === 0) animEntranceStart.start()
                        Connections { target: root; function onNavIndexChanged() { if (navIndex === 0) animEntranceStart.restart() } }

                        // Modern mikro-etkileşim: Hover'da 1.015x büyüme, tıklandığında 0.97x basılma hissi
                        scale: down ? 0.97 : (hovered ? 1.015 : 1.0)
                        transformOrigin: Item.Center
                        Behavior on scale {
                            NumberAnimation { duration: 160; easing.type: Easing.OutCubic }
                        }

                        onClicked: {
                            if (isTranslating) {
                                appBackend.stopTranslation()
                            } else {
                                if (!projectPathField.text || projectPathField.text.trim().length === 0) {
                                    projectPathField.triggerShake()
                                    showToast(appBackend.getTextWithDefault("log_select_game", "Lütfen bir oyun klasörü veya EXE seçin."), "warning")
                                    return
                                }
                                appBackend.startTranslation()
                            }
                        }
                        background: Rectangle {
                            id: startBtnBg
                            radius: 6

                            // Çeviri sırasında çalışan nefes alma (pulsating) animasyonu
                            SequentialAnimation on opacity {
                                running: isTranslating && navIndex === 0
                                loops: Animation.Infinite
                                NumberAnimation { to: 0.78; duration: 900; easing.type: Easing.InOutQuad }
                                NumberAnimation { to: 1.0;  duration: 900; easing.type: Easing.InOutQuad }
                            }

                            gradient: Gradient {
                                orientation: Gradient.Horizontal
                                GradientStop {
                                    position: 0.0
                                    color: isTranslating ? (startButton.hovered ? "#FF8895" : clrError) : (startButton.hovered ? "#D8FFA8" : clrAccent)
                                    Behavior on color { ColorAnimation { duration: 180; easing.type: Easing.OutQuad } }
                                }
                                GradientStop {
                                    position: 1.0
                                    color: isTranslating ? "#D94D60" : (startButton.hovered ? clrAccent : clrAccent2)
                                    Behavior on color { ColorAnimation { duration: 180; easing.type: Easing.OutQuad } }
                                }
                            }

                            // Dış neon ışıma katmanı (Glow border)
                            Rectangle {
                                anchors.fill: parent
                                radius: parent.radius
                                color: "transparent"
                                border.color: isTranslating ? clrError : clrAccent
                                border.width: startButton.hovered || isTranslating ? 2 : 0
                                opacity: startButton.hovered || isTranslating ? 0.6 : 0.0
                                Behavior on opacity { NumberAnimation { duration: 180 } }
                                Behavior on border.width { NumberAnimation { duration: 150 } }
                            }
                        }
                        contentItem: Item {
                            Row {
                                anchors.centerIn: parent
                                spacing: 12

                                Item {
                                    width: 18; height: 18
                                    anchors.verticalCenter: parent.verticalCenter

                                    // STOP İkonu (Windows'un mavi emoji çizmesini önleyen saf beyaz yuvarlatılmış kare)
                                    Rectangle {
                                        anchors.centerIn: parent
                                        width: 14; height: 14; radius: 3
                                        color: "#FFFFFF"
                                        visible: isTranslating
                                        scale: isTranslating ? (startBtnBg.opacity < 0.9 ? 0.92 : 1.08) : 1.0
                                        Behavior on scale { NumberAnimation { duration: 400; easing.type: Easing.InOutQuad } }
                                    }

                                    // START İkonu (⚡ Şimşek)
                                    Label {
                                        anchors.centerIn: parent
                                        text: "▶"
                                        font.pixelSize: 17
                                        color: "#0B0D10"
                                        visible: !isTranslating
                                    }
                                }

                                Label {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: appBackend.uiTrigger, isTranslating ? appBackend.getTextWithDefault("ln_stop_translation", "DETENER PROCESO") : appBackend.getTextWithDefault("ln_start_translation", "EJECUTAR TRADUCCIÓN")
                                    font.pixelSize: 15; font.bold: true
                                    color: isTranslating ? "#FFFFFF" : "#0B0D10"
                                    font.letterSpacing: 1.1
                                }
                            }
                        }
                    }

                    // Native TLID bilgi notu (Dengeli Responsive Banner)
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: ntTipLayout.implicitHeight + 20; radius: 12
                        visible: appBackend.outputMode === "native"
                        color: Qt.rgba(245, 158, 11, 0.08); border.color: Qt.rgba(245, 158, 11, 0.25); border.width: 1
                        RowLayout {
                            id: ntTipLayout
                            anchors.fill: parent; anchors.margins: 12; spacing: 10
                            Label { text: "⚠️"; font.pixelSize: 16; Layout.alignment: Qt.AlignTop }
                            Label {
                                id: ntTipLabel; Layout.fillWidth: true; wrapMode: Text.WordWrap
                                text: appBackend.uiTrigger, appBackend.getTextWithDefault("tip_native_limitation", "Tip: Some games build UI text at runtime (quests + \"(?)\" buttons, NPC schedules, Python f-strings). Native TLID captures static text only. If parts of the interface stay untranslated, switch to Standard mode and re-translate.")
                                color: clrWarn; font.pixelSize: 11; lineHeight: 1.25
                            }
                        }
                    }

                    // ── KART 3: PROCESS STATUS (DURUM BARI) ───────────────
                    Rectangle {
                        id: cardStatus
                        Layout.fillWidth: true
                        Layout.preferredHeight: statusInnerCol.implicitHeight + 44
                        radius: 16; color: cardStatus.hovered ? clrCardHover : clrCard
                        border.color: cardStatus.hovered ? Qt.rgba(184, 243, 107, 0.4) : clrCardBorder
                        border.width: 1
                        property bool hovered: false
                        scale: 1.0
                        transformOrigin: Item.Center
                        Behavior on scale { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
                        Behavior on color { ColorAnimation { duration: 180 } }
                        Behavior on border.color { ColorAnimation { duration: 180 } }
                        Behavior on Layout.preferredHeight { NumberAnimation { duration: 250; easing.type: Easing.OutCubic } }
                        HoverHandler { onHoveredChanged: cardStatus.hovered = hovered }

                        // QW-1 Staggered Entrance
                        transform: Translate { id: animTrStatus; y: 16 }
                        opacity: 0.0
                        SequentialAnimation {
                            id: animEntranceStatus
                            PauseAnimation { duration: 135 }
                            ParallelAnimation {
                                NumberAnimation { target: animTrStatus; property: "y"; to: 0; duration: 240; easing.type: Easing.OutCubic }
                                NumberAnimation { target: cardStatus; property: "opacity"; to: 1.0; duration: 220; easing.type: Easing.OutQuad }
                            }
                        }
                        Component.onCompleted: if (navIndex === 0) animEntranceStatus.start()
                        Connections { target: root; function onNavIndexChanged() { if (navIndex === 0) animEntranceStatus.restart() } }

                        ColumnLayout {
                            id: statusInnerCol
                            anchors.fill: parent; anchors.margins: 22
                            spacing: 14

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8
                                Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("ln_monitor_title", "MONITOR DE EJECUCIÓN"); font.pixelSize: 16; font.bold: true; color: clrTxt }
                                Item { Layout.fillWidth: true }

                                // Canlı aktivite sonar noktası (Radar Pulse Dot)
                                Rectangle {
                                    id: stageActivityDot
                                    width: 8; height: 8; radius: 4
                                    color: currentStage === "completed" ? clrSuccess : (isTranslating ? clrAccent : "transparent")
                                    visible: isTranslating || currentStage === "completed"
                                    scale: isTranslating || currentStage === "completed" ? 1.0 : 0.0

                                    Behavior on color { ColorAnimation { duration: 250 } }
                                    Behavior on scale { NumberAnimation { duration: 200; easing.type: Easing.OutBack } }

                                    Rectangle {
                                        anchors.centerIn: parent
                                        width: parent.width; height: parent.height; radius: width / 2
                                        color: parent.color
                                        opacity: 0.0

                                        SequentialAnimation on scale {
                                            running: isTranslating && navIndex === 0
                                            loops: Animation.Infinite
                                            NumberAnimation { from: 1.0; to: 2.6; duration: 1100; easing.type: Easing.OutQuad }
                                        }
                                        SequentialAnimation on opacity {
                                            running: isTranslating && navIndex === 0
                                            loops: Animation.Infinite
                                            NumberAnimation { from: 0.8; to: 0.0; duration: 1100; easing.type: Easing.OutQuad }
                                        }
                                    }
                                }

                                Row {
                                    spacing: 1
                                    Layout.alignment: Qt.AlignVCenter

                                    Label {
                                        id: stageLabel
                                        text: appBackend.uiTrigger, getStageDisplayText(currentStage)
                                        font.pixelSize: 13; font.bold: true
                                        color: currentStage === "completed" ? clrSuccess : (currentStage === "error" ? clrError : clrAccent)
                                        scale: currentStage === "completed" ? 1.06 : 1.0
                                        transformOrigin: Item.Right

                                        Behavior on color {
                                            ColorAnimation { duration: 250 }
                                        }
                                        Behavior on scale {
                                            NumberAnimation { duration: 320; easing.type: Easing.OutBack; easing.overshoot: 1.6 }
                                        }
                                    }

                                    // Akıcı canlı üç-nokta nabzı (Live Ellipsis Flow - Anti-Freeze Indicator)
                                    Label {
                                        id: stageDots
                                        text: dotCount === 0 ? "" : (dotCount === 1 ? "." : (dotCount === 2 ? ".." : "..."))
                                        property int dotCount: 0
                                        font.pixelSize: 13; font.bold: true
                                        color: clrAccent
                                        visible: isTranslating
                                        width: 14
                                        height: stageLabel.height
                                        verticalAlignment: Text.AlignVCenter

                                        Timer {
                                            interval: 400
                                            repeat: true
                                            running: isTranslating && navIndex === 0
                                            onTriggered: stageDots.dotCount = (stageDots.dotCount + 1) % 4
                                        }
                                    }
                                }
                            }

                            // İlerleme Barı (Akıcı dolum & Shimmer animasyonu)
                            ProgressBar {
                                id: progressBar
                                Layout.fillWidth: true; height: 12
                                value: 0.0

                                background: Rectangle {
                                    radius: 6
                                    color: clrInput
                                    border.color: Qt.rgba(255, 255, 255, 0.06)
                                    border.width: 1
                                }

                                contentItem: Item {
                                    clip: true

                                    Rectangle {
                                        id: progressFill
                                        width: progressBar.visualPosition * parent.width
                                        height: parent.height
                                        radius: 6

                                        Behavior on width {
                                            NumberAnimation { duration: 250; easing.type: Easing.OutCubic }
                                        }

                                        gradient: Gradient {
                                            orientation: Gradient.Horizontal
                                            GradientStop { position: 0.0; color: clrAccent }
                                            GradientStop { position: 1.0; color: clrAccent2 }
                                        }
                                    }

                                    // İşlem sürerken tüm bar boyunca süzülen tarama ışığı (Full-Bar Scanning Shimmer)
                                    Rectangle {
                                        id: progressShimmer
                                        width: 72
                                        height: parent.height
                                        visible: isTranslating
                                        radius: 6
                                        gradient: Gradient {
                                            orientation: Gradient.Horizontal
                                            GradientStop { position: 0.0; color: "transparent" }
                                            GradientStop { position: 0.2; color: Qt.rgba(255, 255, 255, 0.08) }
                                            GradientStop { position: 0.5; color: Qt.rgba(255, 255, 255, 0.38) }
                                            GradientStop { position: 0.8; color: Qt.rgba(255, 255, 255, 0.08) }
                                            GradientStop { position: 1.0; color: "transparent" }
                                        }

                                        NumberAnimation on x {
                                            running: isTranslating && navIndex === 0
                                            loops: Animation.Infinite
                                            from: -progressShimmer.width
                                            to: progressBar.width + progressShimmer.width
                                            duration: 1800
                                            easing.type: Easing.Linear
                                        }
                                    }
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                Label { id: progressLabel; text: appBackend.uiTrigger, appBackend.getTextWithDefault("ln_lines_processed", "Elementos procesados: 0 / 0"); font.pixelSize: 12; color: clrTxt2 }
                                Item { Layout.fillWidth: true }
                                Label { text: Math.round(progressBar.value * 100) + "%"; font.pixelSize: 13; font.bold: true; color: clrTxt }
                            }

                            // İstatistik Kartı Açılımı (QW-2 Celebration Spring & Badge Bounce)
                            RowLayout {
                                id: statsRow
                                Layout.fillWidth: true
                                visible: statsVisible

                                Rectangle {
                                    id: statsBannerRect
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 46
                                    radius: 12
                                    color: statsPartial ? clrWarnDim : clrSuccessDim
                                    border.color: statsPartial ? clrWarn : clrSuccess
                                    border.width: 1
                                    clip: true

                                    scale: statsVisible ? 1.0 : 0.90
                                    opacity: statsVisible ? 1.0 : 0.0
                                    transformOrigin: Item.Center

                                    Behavior on scale {
                                        NumberAnimation { duration: 320; easing.type: Easing.OutBack; easing.overshoot: 1.4 }
                                    }
                                    Behavior on opacity {
                                        NumberAnimation { duration: 220; easing.type: Easing.OutQuad }
                                    }

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: 12
                                        anchors.rightMargin: 14
                                        spacing: 10

                                        // Kutlama rozeti (Spring bounce tick)
                                        Rectangle {
                                            id: successBadge
                                            width: 24; height: 24; radius: 14
                                            color: statsPartial ? clrWarn : clrSuccess
                                            scale: statsVisible ? 1.0 : 0.0
                                            opacity: statsVisible ? 1.0 : 0.0
                                            transformOrigin: Item.Center

                                            Behavior on scale {
                                                NumberAnimation { duration: 420; easing.type: Easing.OutBack; easing.overshoot: 1.8 }
                                            }
                                            Behavior on opacity {
                                                NumberAnimation { duration: 200 }
                                            }

                                            Label {
                                                anchors.centerIn: parent
                                                text: statsPartial ? "!" : "✓"
                                                color: "#FFFFFF"
                                                font.bold: true
                                                font.pixelSize: 13
                                            }
                                        }

                                        Label {
                                            text: appBackend.uiTrigger, statsPartial
                                                  ? appBackend.getTextWithDefault(statsScope === "mod" ? "stats_mod_partial_banner" : "stats_partial_banner",
                                                        statsScope === "mod" ? "MOD generated with pending texts" : "Finished with pending lines")
                                                  : appBackend.getTextWithDefault(statsScope === "mod" ? "stats_mod_done_banner" : "stats_completed_banner",
                                                        statsScope === "mod" ? "MOD generated" : "Translation completed")
                                            font.bold: true
                                            color: statsPartial ? clrWarn : clrSuccess
                                            font.pixelSize: 13
                                        }

                                        Item { Layout.fillWidth: true }

                                        Label {
                                            text: appBackend.uiTrigger, appBackend.getTextWithDefault("stats_summary_total", "Total:") + " " + totalLines
                                                  + " | " + appBackend.getTextWithDefault("stats_summary_translated", "Translated:") + " " + translatedLines + " (" + successRate.toFixed(1) + "%)"
                                                  + " | " + appBackend.getTextWithDefault("stats_summary_unchanged", "Same as original:") + " " + unchangedLines
                                                  + " | " + appBackend.getTextWithDefault("stats_summary_pending", "Pending:") + " " + pendingLines
                                            color: clrTxt
                                            font.pixelSize: 13
                                            font.bold: true
                                            elide: Text.ElideLeft
                                            Layout.maximumWidth: statsBannerRect.width * 0.62
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // ── KART 4: LOG CONSOLE SUMMARY (MİNİ LOG PANELİ) ───────
                    Rectangle {
                        id: cardLog
                        Layout.fillWidth: true
                        Layout.preferredHeight: 185
                        radius: 16; color: cardLog.hovered ? clrCardHover : clrCard
                        border.color: cardLog.hovered ? Qt.rgba(184, 243, 107, 0.4) : clrCardBorder
                        border.width: 1
                        property bool hovered: false
                        scale: 1.0
                        transformOrigin: Item.Center
                        Behavior on scale { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
                        Behavior on color { ColorAnimation { duration: 180 } }
                        Behavior on border.color { ColorAnimation { duration: 180 } }
                        HoverHandler { onHoveredChanged: cardLog.hovered = hovered }

                        // QW-1 Staggered Entrance
                        transform: Translate { id: animTrLog; y: 16 }
                        opacity: 0.0
                        SequentialAnimation {
                            id: animEntranceLog
                            PauseAnimation { duration: 180 }
                            ParallelAnimation {
                                NumberAnimation { target: animTrLog; property: "y"; to: 0; duration: 240; easing.type: Easing.OutCubic }
                                NumberAnimation { target: cardLog; property: "opacity"; to: 1.0; duration: 220; easing.type: Easing.OutQuad }
                            }
                        }
                        Component.onCompleted: if (navIndex === 0) animEntranceLog.start()
                        Connections { target: root; function onNavIndexChanged() { if (navIndex === 0) animEntranceLog.restart() } }

                        ColumnLayout {
                            anchors.fill: parent; anchors.margins: 18
                            spacing: 10

                            RowLayout {
                                Layout.fillWidth: true
                                Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("card_log_title", "Log Console Summary"); font.pixelSize: 15; font.bold: true; color: clrTxt }
                                Item { Layout.fillWidth: true }
                                Button {
                                    height: 28; text: appBackend.uiTrigger, "📜 " + appBackend.getTextWithDefault("view_all_logs", "Tüm Logları Aç ->")
                                    scale: down ? 0.96 : (hovered ? 1.04 : 1.0)
                                    transformOrigin: Item.Center
                                    Behavior on scale { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
                                    onClicked: navIndex = 2
                                    background: Rectangle {
                                        radius: 6
                                        color: parent.hovered ? Qt.rgba(184, 243, 107, 0.1) : "transparent"
                                        Behavior on color { ColorAnimation { duration: 140 } }
                                    }
                                    contentItem: Label {
                                        text: parent.text; color: parent.hovered ? "#FFFFFF" : clrAccent
                                        font.pixelSize: 12; font.underline: true
                                        Behavior on color { ColorAnimation { duration: 140 } }
                                    }
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true; Layout.fillHeight: true; radius: 12; color: clrInput; border.color: clrCardBorder; border.width: 1
                                ListView {
                                    id: logListView
                                    anchors.fill: parent; anchors.margins: 10; clip: true
                                    model: logModel
                                    delegate: RowLayout {
                                        width: logListView.width - 20; spacing: 12
                                        Label { text: model.ts; color: clrTxtDim; font.pixelSize: 11; font.family: "Consolas" }
                                        Label { text: logPrefix(model.level); color: logColor(model.level); font.bold: true; font.pixelSize: 11 }
                                        Label { text: model.message; color: logColor(model.level); font.pixelSize: 11; Layout.fillWidth: true; elide: Text.ElideRight }
                                    }
                                }
                            }
                        }
                    }

                    Item { height: 24 }
                }
            }
        }

            // ═════════════════════════════════════════════════════════════
            // SEKME 1: SETTINGS (TAM SAYFA GELİŞMİŞ AYARLAR)
            // ═════════════════════════════════════════════════════════════
            Item {
                id: pageSettings
                Layout.fillWidth: true
                Layout.fillHeight: true

                property int settingsSubTab: 0 // 0: Genel & Çıktı, 1: Yapay Zeka (AI), 2: Performans & Ağ

                // ── SABİT STICKY HEADER & SUB-NAVIGATION ──────────────
                Rectangle {
                    id: settingsStickyHeader
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    height: root.compactHeight ? 94 : 116
                    color: clrBg
                    z: 10

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.leftMargin: root.compactWidth ? 16 : 32
                        anchors.rightMargin: root.compactWidth ? 16 : 32
                        anchors.topMargin: root.compactHeight ? 8 : 12
                        anchors.bottomMargin: root.compactHeight ? 7 : 10
                        spacing: root.compactHeight ? 7 : 10

                        RowLayout {
                            Layout.fillWidth: true
                            ColumnLayout {
                                spacing: 2
                                Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("ln_config_title", "Laboratorio de configuración"); font.pixelSize: root.compactHeight ? 20 : 24; font.bold: true; color: clrTxt }
                                Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("ln_config_desc", "Ajusta comportamiento, salida, proveedores, rendimiento y preferencias de la aplicación."); font.pixelSize: 12; color: clrTxt2 }
                            }
                        }

                        // Segmented Sub-Tab Bar
                        RowLayout {
                            spacing: 8

                            Button {
                                height: 34
                                Layout.preferredWidth: Math.max(150, implicitContentWidth + 24)
                                onClicked: pageSettings.settingsSubTab = 0
                                background: Rectangle {
                                    radius: 10
                                    color: pageSettings.settingsSubTab === 0 ? Qt.rgba(184, 243, 107, 0.15) : (parent.hovered ? clrCardHover : "transparent")
                                    border.color: pageSettings.settingsSubTab === 0 ? clrAccent : clrCardBorder
                                    border.width: 1
                                    Behavior on color { ColorAnimation { duration: 140 } }
                                }
                                contentItem: Label {
                                    text: appBackend.uiTrigger, "🖥️ " + appBackend.getTextWithDefault("subtab_general", "Genel & Çıktı")
                                    color: pageSettings.settingsSubTab === 0 ? clrAccent : clrTxt2
                                    font.bold: pageSettings.settingsSubTab === 0
                                    font.pixelSize: 12
                                    horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                                }
                            }

                            Button {
                                height: 34
                                Layout.preferredWidth: Math.max(160, implicitContentWidth + 24)
                                onClicked: pageSettings.settingsSubTab = 1
                                background: Rectangle {
                                    radius: 10
                                    color: pageSettings.settingsSubTab === 1 ? Qt.rgba(184, 243, 107, 0.15) : (parent.hovered ? clrCardHover : "transparent")
                                    border.color: pageSettings.settingsSubTab === 1 ? clrAccent : clrCardBorder
                                    border.width: 1
                                    Behavior on color { ColorAnimation { duration: 140 } }
                                }
                                contentItem: Label {
                                    text: appBackend.uiTrigger, "🤖 " + appBackend.getTextWithDefault("subtab_ai", "Yapay Zeka (AI)")
                                    color: pageSettings.settingsSubTab === 1 ? clrAccent : clrTxt2
                                    font.bold: pageSettings.settingsSubTab === 1
                                    font.pixelSize: 12
                                    horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                                }
                            }

                            Button {
                                height: 34
                                Layout.preferredWidth: Math.max(160, implicitContentWidth + 24)
                                onClicked: pageSettings.settingsSubTab = 2
                                background: Rectangle {
                                    radius: 10
                                    color: pageSettings.settingsSubTab === 2 ? Qt.rgba(184, 243, 107, 0.15) : (parent.hovered ? clrCardHover : "transparent")
                                    border.color: pageSettings.settingsSubTab === 2 ? clrAccent : clrCardBorder
                                    border.width: 1
                                    Behavior on color { ColorAnimation { duration: 140 } }
                                }
                                contentItem: Label {
                                    text: appBackend.uiTrigger, "⚡ " + appBackend.getTextWithDefault("subtab_perf", "Performans & Ağ")
                                    color: pageSettings.settingsSubTab === 2 ? clrAccent : clrTxt2
                                    font.bold: pageSettings.settingsSubTab === 2
                                    font.pixelSize: 12
                                    horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                                }
                            }

                            Item { Layout.fillWidth: true }
                        }
                    }

                    Rectangle {
                        anchors.bottom: parent.bottom
                        anchors.left: parent.left; anchors.right: parent.right
                        height: 1
                        color: clrCardBorder
                        opacity: 0.6
                    }
                }

                // ── KAYDIRILABİLİR İÇERİK ALANI ───────────────────────
                ScrollView {
                    id: viewSettings
                    anchors.top: settingsStickyHeader.bottom
                    anchors.bottom: parent.bottom
                    anchors.left: parent.left
                    anchors.right: parent.right
                    clip: true
                    contentWidth: availableWidth
                    contentHeight: settingsContent.implicitHeight + (root.responsivePageMargin * 2)
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                    ScrollBar.vertical.policy: root.needsPageScroll(viewSettings.contentHeight, viewSettings.availableHeight)
                                                   ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff

                    transform: Translate { id: animTrSettings; y: 14 }
                    opacity: 0.0
                    ParallelAnimation {
                        id: animEntranceSettings
                        NumberAnimation { target: animTrSettings; property: "y"; from: 14; to: 0; duration: 220; easing.type: Easing.OutCubic }
                        NumberAnimation { target: viewSettings; property: "opacity"; from: 0.0; to: 1.0; duration: 180; easing.type: Easing.OutQuad }
                    }
                    onVisibleChanged: if (visible) animEntranceSettings.restart()

                    ColumnLayout {
                        id: settingsContent
                        y: root.responsivePageMargin
                        width: Math.max(0, Math.min(viewSettings.availableWidth - (root.responsivePageMargin * 2), 1180))
                        anchors.horizontalCenter: parent.horizontalCenter
                        spacing: 20

                        Item { height: 8 }

                    // 1. ARAYÜZ & SİSTEM AYARLARI KARTI (GENEL SEKME)
                    Rectangle {
                        id: cardUiSettings
                        visible: pageSettings.settingsSubTab === 0
                        Layout.fillWidth: true
                        // The active UI language determines the real text height.
                        // Longer translations grow this card only as much as needed.
                        Layout.preferredHeight: uiSettingsCol.implicitHeight + 44
                        radius: 16; color: clrCard; border.color: clrCardBorder; border.width: 1
                        Behavior on Layout.preferredHeight { NumberAnimation { duration: 160 } }

                        ColumnLayout {
                            id: uiSettingsCol
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: 22
                            spacing: 14
                            Label { text: appBackend.uiTrigger, "🖥️ " + appBackend.getTextWithDefault("settings_section_ui", "Arayüz & Sistem Ayarları"); font.pixelSize: 16; font.bold: true; color: clrAccent }

                            RowLayout {
                                Layout.fillWidth: true
                                Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("ui_language_label", "Arayüz Dili (UI Language):"); color: clrTxt; font.bold: true; font.pixelSize: 13 }
                                ComboBox {
                                    id: uiLanguageCombo
                                    Layout.preferredWidth: 240; height: 38
                                    model: appBackend.getAvailableUILanguages()
                                    textRole: "name"; valueRole: "code"
                                    Connections {
                                        target: appBackend
                                        function onUiLanguagesChanged() {
                                            uiLanguageCombo.model = appBackend.getAvailableUILanguages()
                                            uiLanguageCombo.syncUILanguage()
                                        }
                                    }
                                    function syncUILanguage() {
                                        var cur = appBackend.getCurrentUILanguage() || "en"
                                        var idx = uiLanguageCombo.indexOfValue(cur)
                                        if (idx >= 0) uiLanguageCombo.currentIndex = idx
                                    }
                                    Component.onCompleted: syncUILanguage()
                                    Connections {
                                        target: appBackend
                                        function onUiTriggerChanged() { uiLanguageCombo.syncUILanguage() }
                                    }
                                    background: Rectangle { radius: 10; color: clrInput; border.color: clrCardBorder; border.width: 1 }
                                    contentItem: Label { leftPadding: 14; text: uiLanguageCombo.displayText; color: clrTxt; font.pixelSize: 12; verticalAlignment: Text.AlignVCenter }
                                    onActivated: appBackend.setUILanguage(currentValue)
                                    delegate: ItemDelegate { width: uiLanguageCombo.width; contentItem: Label { text: modelData.name; color: clrTxt; font.pixelSize: 12; leftPadding: 14 } background: Rectangle { color: hovered ? Qt.rgba(184, 243, 107, 0.12) : "transparent" } }
                                    popup: Popup { y: uiLanguageCombo.height; width: uiLanguageCombo.width; implicitHeight: 240; padding: 4; contentItem: ListView { clip: true; model: uiLanguageCombo.delegateModel; ScrollBar.vertical: ScrollBar {} } background: Rectangle { color: clrCard; radius: 10; border.color: clrCardBorder; border.width: 1 } }
                                }
                                Item { Layout.fillWidth: true }
                            }

                            RowLayout {
                                Layout.fillWidth: true; spacing: 16
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 2
                                    Label { text: appBackend.uiTrigger, "🔔 " + appBackend.getTextWithDefault("enable_desktop_notifications_label", "Masaüstü Bildirimleri"); color: clrTxt; font.bold: true; font.pixelSize: 13 }
                                    Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("enable_desktop_notifications_tooltip", "Çeviri tamamlandığında veya hata oluştuğunda masaüstü bildirimi göster."); color: clrTxt2; font.pixelSize: 11; wrapMode: Text.WordWrap; lineHeight: 1.15; Layout.fillWidth: true; Layout.preferredHeight: implicitHeight }
                                }
                                Switch {
                                    checked: appBackend.enableDesktopNotifications
                                    onToggled: appBackend.enableDesktopNotifications = checked
                                }
                            }
                        }
                    }

                    // 2. ÇIKTI ÜRETİM MODU & ÇEVİRİ BELLEĞİ (NATIVE TLID vs STRINGS & TM CACHE)
                    Rectangle {
                        id: cardOutputSettings
                        visible: pageSettings.settingsSubTab === 0
                        Layout.fillWidth: true
                        Layout.preferredHeight: outCol.implicitHeight + 44
                        radius: 16; color: clrCard; border.color: clrCardBorder; border.width: 1
                        Behavior on Layout.preferredHeight { NumberAnimation { duration: 200 } }

                        ColumnLayout {
                            id: outCol
                            anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                            anchors.margins: 22; spacing: 18

                            Label { text: appBackend.uiTrigger, "📦 " + appBackend.getTextWithDefault("settings_section_output", "Çıktı Üretim Modu & Çeviri Belleği (Output & TM Cache)"); font.pixelSize: 16; font.bold: true; color: clrAccent }

                            // KATMAN 1: GÖRSEL ÇİFT BUTONLU SEGMENTED SEÇİCİ (STRINGS vs NATIVE TLID)
                            ColumnLayout {
                                Layout.fillWidth: true; spacing: 10

                                Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("label_output_mode", "Ren'Py Çıktı Formatı Seçimi (Output Generation Mode):"); color: clrTxt; font.bold: true; font.pixelSize: 13 }

                                RowLayout {
                                    Layout.fillWidth: true; spacing: 14

                                    // Buton 1: Strings Modu
                                    Button {
                                        id: btnStringsMode
                                        Layout.fillWidth: true; height: 48
                                        onClicked: appBackend.outputMode = "strings"

                                        background: Rectangle {
                                            radius: 12
                                            color: appBackend.outputMode === "strings" ? Qt.rgba(184, 243, 107, 0.15) : (btnStringsMode.hovered ? Qt.rgba(1, 1, 1, 0.08) : clrInput)
                                            border.color: appBackend.outputMode === "strings" ? clrAccent : clrCardBorder
                                            border.width: appBackend.outputMode === "strings" ? 2 : 1
                                            Behavior on color { ColorAnimation { duration: 150 } }
                                        }

                                        contentItem: RowLayout {
                                            anchors.centerIn: parent; spacing: 8
                                            Label { text: appBackend.outputMode === "strings" ? "●" : "○"; color: appBackend.outputMode === "strings" ? clrAccent : clrTxtDim; font.pixelSize: 16 }
                                            Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("mode_strings_btn", "📋 Standard (strings.json)"); color: appBackend.outputMode === "strings" ? clrAccent : clrTxt; font.bold: appBackend.outputMode === "strings"; font.pixelSize: 12 }
                                        }
                                    }

                                    // Buton 2: Native TLID Modu
                                    Button {
                                        id: btnNativeMode
                                        Layout.fillWidth: true; height: 48
                                        onClicked: appBackend.outputMode = "native"

                                        background: Rectangle {
                                            radius: 12
                                            color: appBackend.outputMode === "native" ? Qt.rgba(184, 243, 107, 0.15) : (btnNativeMode.hovered ? Qt.rgba(1, 1, 1, 0.08) : clrInput)
                                            border.color: appBackend.outputMode === "native" ? clrAccent : clrCardBorder
                                            border.width: appBackend.outputMode === "native" ? 2 : 1
                                            Behavior on color { ColorAnimation { duration: 150 } }
                                        }

                                        contentItem: RowLayout {
                                            anchors.centerIn: parent; spacing: 6
                                            Label { text: appBackend.outputMode === "native" ? "●" : "○"; color: appBackend.outputMode === "native" ? clrAccent : clrTxtDim; font.pixelSize: 16 }
                                            Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("mode_native_btn", "⚡ Native TLID"); color: appBackend.outputMode === "native" ? clrAccent : clrTxt; font.bold: appBackend.outputMode === "native"; font.pixelSize: 12 }
                                            Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("badge_recommended", "💎 Recommended"); color: clrSuccess; font.pixelSize: 10; font.bold: true }
                                        }
                                    }
                                }

                                Rectangle {
                                    Layout.fillWidth: true; Layout.preferredHeight: descLayout.implicitHeight + 16
                                    radius: 10; color: Qt.rgba(1, 1, 1, 0.03); border.color: clrCardBorder; border.width: 1
                                    RowLayout {
                                        id: descLayout; anchors.fill: parent; anchors.margins: 8; spacing: 8
                                        Label { text: "💡"; font.pixelSize: 14 }
                                        Label {
                                            id: descLabel; Layout.fillWidth: true; wrapMode: Text.WordWrap
                                            text: appBackend.outputMode === "native" ?
                                                  (appBackend.uiTrigger, appBackend.getTextWithDefault("desc_native_mode", "Ren'Py built-in translate blocks for dialogues + auto-export translate strings: for UI. Zero Python scripts during gameplay — pure native speed. Works for ~90% of games. Known limitation: Python {variable} texts and runtime-concatenated strings may not be captured. Switch to Standard if you see untranslated screen elements.")) :
                                                  (appBackend.uiTrigger, appBackend.getTextWithDefault("desc_strings_mode", "Complete mode for text that can change while the game is running. It also covers dynamic text and text built from several parts. It uses a little more memory and is recommended for complex interfaces."))
                                            color: clrTxt2; font.pixelSize: 11
                                            lineHeight: 1.15
                                        }
                                    }
                                }

                                // Tip: when to use Standard mode
                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: tipLayout.implicitHeight + 16
                                    radius: 10; color: Qt.rgba(245, 158, 11, 0.08); border.color: Qt.rgba(245, 158, 11, 0.25); border.width: 1
                                    visible: appBackend.outputMode === "native"
                                    RowLayout {
                                        id: tipLayout
                                        anchors.fill: parent; anchors.margins: 8; spacing: 8
                                        Label { text: "⚠️"; font.pixelSize: 14 }
                                        Label {
                                            id: tipLabel; Layout.fillWidth: true; wrapMode: Text.WordWrap
                                            text: appBackend.uiTrigger, appBackend.getTextWithDefault("tip_native_limitation", "Some games define UI text in Python variables (quests, schedules, etc.). If you see untranslated screen text, switch to Standard mode — it handles these better.")
                                            color: clrWarn; font.pixelSize: 11
                                            lineHeight: 1.15
                                        }
                                    }
                                }
                            }

                            Rectangle { Layout.fillWidth: true; height: 1; color: clrCardBorder }

                            // Integración segura del idioma en el selector nativo del juego
                            RowLayout {
                                Layout.fillWidth: true; spacing: 10
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("activate_language_title", "Integrate language into the game selector"); color: clrTxt; font.bold: true; font.pixelSize: 13 }
                                    Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("activate_language_desc", "Safely adds the translated language to the game's existing selector when LinguaNova can identify it. It never forces the language at startup."); color: clrTxt2; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap; lineHeight: 1.15 }
                                }
                                Switch { checked: appBackend.activateLanguageOnLaunch; onToggled: appBackend.activateLanguageOnLaunch = checked }
                            }

                            Rectangle { Layout.fillWidth: true; height: 1; color: clrCardBorder }

                            // KATMAN 2: ÇEVİRİ BELLEĞİ (TM CACHE) TOGGLE
                            RowLayout {
                                Layout.fillWidth: true; spacing: 16

                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 3
                                    Label { text: appBackend.uiTrigger, "💾 " + appBackend.getTextWithDefault("lite_cache_title", "Çeviri Belleği (TM Cache) Kullan"); color: clrTxt; font.bold: true; font.pixelSize: 13 }
                                    Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("lite_cache_desc", "Daha önce çevrilen satırları hatırlar, aynı cümle tekrar geldiğinde anında bellekten getirir."); color: clrTxt2; font.pixelSize: 11; wrapMode: Text.WordWrap; lineHeight: 1.15; Layout.fillWidth: true; Layout.preferredHeight: implicitHeight }
                                }

                                Switch {
                                    checked: appBackend.useCache
                                    onToggled: appBackend.useCache = checked
                                }
                            }
                        }
                    }

                    // 3. BAKIM VE TEHLİKELİ BÖLGE KARTI (DANGER ZONE & MAINTENANCE)
                    Rectangle {
                        id: cardDangerZone
                        visible: pageSettings.settingsSubTab === 0
                        Layout.fillWidth: true
                        Layout.preferredHeight: dangerCol.implicitHeight + 40
                        radius: 16
                        color: Qt.rgba(239, 68, 68, 0.04)
                        border.color: Qt.rgba(239, 68, 68, 0.3)
                        border.width: 1

                        ColumnLayout {
                            id: dangerCol
                            anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                            anchors.margins: 22; spacing: 16

                            Label { text: appBackend.uiTrigger, "🛡️ " + appBackend.getTextWithDefault("danger_zone_title", "Bakım ve Veri Sıfırlama (Maintenance & Reset)"); font.pixelSize: 15; font.bold: true; color: clrError }

                            // Satır 1: Çeviri Belleğini Temizle
                            RowLayout {
                                Layout.fillWidth: true; spacing: 16
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 2
                                    Label { text: appBackend.uiTrigger, "🧹 " + appBackend.getTextWithDefault("clear_tm_title", "Çeviri Belleğini (TM) Temizle"); color: clrTxt; font.bold: true; font.pixelSize: 13 }
                                    Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("clear_tm_desc", "Daha önce önbelleğe alınan tüm çeviri eşleşmelerini temizler."); color: clrTxt2; font.pixelSize: 11 }
                                }
                                Button {
                                    Layout.preferredWidth: 180; height: 38
                                    text: appBackend.uiTrigger, "🧹 " + appBackend.getTextWithDefault("lite_clear_cache_btn", "Önbelleği Temizle")
                                    onClicked: if (appBackend.clearTranslationCache()) showToast(appBackend.getTextWithDefault("cache_cleared_toast", "Translation cache cleared."), "success")
                                    background: Rectangle { radius: 10; color: parent.hovered ? "#991B1B" : "#7F1D1D"; border.color: "#B91C1C"; border.width: 1 }
                                    contentItem: Label { text: parent.text; color: "white"; font.bold: true; font.pixelSize: 11; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                }
                            }

                            Rectangle { Layout.fillWidth: true; height: 1; color: Qt.rgba(239, 68, 68, 0.2) }

                            // Satır 2: Fabrika Ayarlarına Sıfırla
                            RowLayout {
                                Layout.fillWidth: true; spacing: 16
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 2
                                    Label { text: appBackend.uiTrigger, "🔄 " + appBackend.getTextWithDefault("factory_reset_title", "Fabrika Ayarlarına Sıfırla"); color: clrTxt; font.bold: true; font.pixelSize: 13 }
                                    Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("factory_reset_desc", "Tüm ayarları, API anahtarlarını ve sözlüğü siler; programı varsayılan haline döndürür."); color: clrTxt2; font.pixelSize: 11 }
                                }
                                Button {
                                    Layout.preferredWidth: 180; height: 38
                                    text: appBackend.uiTrigger, "🔄 " + appBackend.getTextWithDefault("factory_reset_btn", "Sıfırla")
                                    onClicked: factoryResetDialog.open()
                                    background: Rectangle { radius: 10; color: parent.hovered ? "#991B1B" : "#7F1D1D"; border.color: "#B91C1C"; border.width: 1 }
                                    contentItem: Label { text: parent.text; color: "white"; font.bold: true; font.pixelSize: 11; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                }
                            }
                        }
                    }

                    // PERFORMANS VE PARAMETRELER KARTI
                    Rectangle {
                        id: cardPerfSettings
                        visible: pageSettings.settingsSubTab === 2
                        Layout.fillWidth: true
                        Layout.preferredHeight: perfCol.implicitHeight + 44
                        radius: 16; color: clrCard; border.color: clrCardBorder; border.width: 1
                        Behavior on Layout.preferredHeight { NumberAnimation { duration: 200 } }

                        ColumnLayout {
                            id: perfCol
                            anchors.fill: parent; anchors.margins: 22; spacing: 16
                            Label { text: appBackend.uiTrigger, "⚡ " + appBackend.getTextWithDefault("settings_section_perf", "Performans & Bağlantı Parametreleri"); font.pixelSize: 16; font.bold: true; color: clrAccent }

                            RowLayout {
                                Layout.fillWidth: true; spacing: 20
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 6
                                    Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("concurrency_label", "Concurrent Threads") + ": " + Math.round(threadsSlider.value); color: clrTxt; font.bold: true; font.pixelSize: 13; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                                    Slider { id: threadsSlider; Layout.fillWidth: true; from: 1; to: 32; stepSize: 1; value: appBackend.maxConcurrentThreads; onMoved: appBackend.maxConcurrentThreads = value }
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 6
                                    Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("delay_label", "Request Delay") + ": " + delaySlider.value.toFixed(2) + "s"; color: clrTxt; font.bold: true; font.pixelSize: 13; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                                    Slider { id: delaySlider; Layout.fillWidth: true; from: 0.0; to: 3.0; stepSize: 0.05; value: appBackend.requestDelay; onMoved: appBackend.requestDelay = value }
                                }
                            }

                            ColumnLayout {
                                Layout.fillWidth: true; spacing: 6
                                Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("batch_label", "Batch Size") + ": " + Math.round(batchSlider.value); color: clrTxt; font.bold: true; font.pixelSize: 13; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                                Slider { id: batchSlider; Layout.fillWidth: true; from: 10; to: 500; stepSize: 10; value: appBackend.maxBatchSize; onMoved: appBackend.maxBatchSize = value }
                            }

                            Rectangle { Layout.fillWidth: true; height: 1; color: clrCardBorder }

                            // 2-Sütunlu Dengeli Switch Izgarası
                            GridLayout {
                                Layout.fillWidth: true
                                columns: 2
                                columnSpacing: 24
                                rowSpacing: 16

                                // Switch 1: Multi-Endpoint
                                RowLayout {
                                    Layout.fillWidth: true; spacing: 10
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("multi_endpoint_title", "Multi-Endpoint (Mirror)"); color: clrTxt; font.bold: true; font.pixelSize: 13 }
                                        Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("multi_endpoint_desc", "Distributes requests across Google servers."); color: clrTxt2; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap; lineHeight: 1.15 }
                                    }
                                    Switch { checked: appBackend.useMultiEndpoint; onToggled: appBackend.useMultiEndpoint = checked }
                                }

                                // Switch 2: Parallel Batch
                                RowLayout {
                                    Layout.fillWidth: true; spacing: 10
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("parallel_batch_label", "Parallel Batch Requests"); color: clrTxt; font.bold: true; font.pixelSize: 13 }
                                        Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("parallel_batch_desc", "Send multiple requests simultaneously. Disable if rate limited."); color: clrTxt2; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap; lineHeight: 1.15 }
                                    }
                                    Switch {
                                        id: parallelBatchSwitch
                                        checked: appBackend.enableParallelBatch
                                        onToggled: appBackend.enableParallelBatch = checked
                                    }
                                }

                                // Switch 3: RPYC AST Reader
                                RowLayout {
                                    Layout.fillWidth: true; spacing: 10
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("rpyc_reader_title", "RPYC AST Reader"); color: clrTxt; font.bold: true; font.pixelSize: 13 }
                                        Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("rpyc_reader_desc", "Reads compiled .rpyc files directly."); color: clrTxt2; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap; lineHeight: 1.15 }
                                    }
                                    Switch { checked: appBackend.enableRpycReader; onToggled: appBackend.enableRpycReader = checked }
                                }

                                // Switch 4: Stateful Lexer
                                RowLayout {
                                    Layout.fillWidth: true; spacing: 10
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("stateful_lexer_title", "Stateful Lexer Engine (Experimental)"); color: clrTxt; font.bold: true; font.pixelSize: 13 }
                                        Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("stateful_lexer_desc", "Advanced script analysis. Enable it only when you need a deeper text inspection."); color: clrTxt2; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap; lineHeight: 1.15 }
                                    }
                                    Switch { checked: appBackend.enableStatefulLexer; onToggled: appBackend.enableStatefulLexer = checked }
                                }
                            }
                        }
                    }

                    // AI MOTOR KARTI (SEÇİLİ MOTORA DUYARLI TAM KAPSAMLI YAPILANDIRMA)
                    Rectangle {
                        id: cardAiConfig
                        visible: pageSettings.settingsSubTab === 1
                        Layout.fillWidth: true
                        Layout.preferredHeight: aiCol.implicitHeight + 44
                        radius: 16; color: clrCard; border.color: clrCardBorder; border.width: 1
                        Behavior on Layout.preferredHeight { NumberAnimation { duration: 200 } }

                        ColumnLayout {
                            id: aiCol
                            anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                            anchors.margins: 22; spacing: 16

                            Label { text: appBackend.uiTrigger, "🤖 " + appBackend.getTextWithDefault("settings_section_ai", "AI Engine Configuration"); font.pixelSize: 16; font.bold: true; color: clrAccent }

                            // OpenAI / DeepSeek Ayarları
                            ColumnLayout {
                                Layout.fillWidth: true; spacing: 14
                                visible: appBackend.selectedEngine === "openai" || appBackend.selectedEngine === "deepseek"

                                RowLayout {
                                    Layout.fillWidth: true; spacing: 18
                                    ColumnLayout {
                                        Layout.fillWidth: true; spacing: 5
                                        Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("label_openai_key", "OpenAI / DeepSeek API Key:"); color: clrTxt; font.bold: true; font.pixelSize: 13 }
                                        TextField {
                                            Layout.fillWidth: true; height: 40; text: appBackend.openaiApiKey; echoMode: TextInput.Password; placeholderText: "sk-..."
                                            onEditingFinished: appBackend.openaiApiKey = text
                                            background: Rectangle {
                                                radius: 10; color: clrInput
                                                border.color: parent.activeFocus ? clrAccent : clrCardBorder; border.width: 1
                                                Behavior on border.color { ColorAnimation { duration: 150 } }
                                                Rectangle {
                                                    anchors.fill: parent; anchors.margins: -3; radius: parent.radius + 2; color: "transparent"
                                                    border.color: clrAccent; border.width: 2; opacity: parent.parent.activeFocus ? 0.35 : 0.0
                                                    scale: parent.parent.activeFocus ? 1.0 : 0.98
                                                    Behavior on opacity { NumberAnimation { duration: 180; easing.type: Easing.OutQuad } }
                                                    Behavior on scale { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
                                                }
                                            }
                                        }
                                    }
                                    ColumnLayout {
                                        Layout.fillWidth: true; spacing: 5
                                        Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("label_openai_model", "Model Name:"); color: clrTxt; font.bold: true; font.pixelSize: 13 }
                                        TextField {
                                            Layout.fillWidth: true; height: 40; text: appBackend.openaiModel; placeholderText: appBackend.selectedEngine === "deepseek" ? "deepseek-v4-flash" : "gpt-4o-mini"
                                            onEditingFinished: appBackend.openaiModel = text
                                            background: Rectangle {
                                                radius: 10; color: clrInput
                                                border.color: parent.activeFocus ? clrAccent : clrCardBorder; border.width: 1
                                                Behavior on border.color { ColorAnimation { duration: 150 } }
                                                Rectangle {
                                                    anchors.fill: parent; anchors.margins: -3; radius: parent.radius + 2; color: "transparent"
                                                    border.color: clrAccent; border.width: 2; opacity: parent.parent.activeFocus ? 0.35 : 0.0
                                                    scale: parent.parent.activeFocus ? 1.0 : 0.98
                                                    Behavior on opacity { NumberAnimation { duration: 180; easing.type: Easing.OutQuad } }
                                                    Behavior on scale { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
                                                }
                                            }
                                        }
                                    }
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 5
                                    Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("openai_base_url_label", "Base URL (Optional, empty for default):"); color: clrTxt; font.bold: true; font.pixelSize: 13 }
                                    TextField {
                                        Layout.fillWidth: true; height: 40; text: appBackend.openaiBaseUrl; placeholderText: appBackend.selectedEngine === "deepseek" ? "https://api.deepseek.com/v1" : "https://api.openai.com/v1"
                                        onEditingFinished: appBackend.openaiBaseUrl = text
                                        background: Rectangle {
                                            radius: 10; color: clrInput
                                            border.color: parent.activeFocus ? clrAccent : clrCardBorder; border.width: 1
                                            Behavior on border.color { ColorAnimation { duration: 150 } }
                                            Rectangle {
                                                anchors.fill: parent; anchors.margins: -3; radius: parent.radius + 2; color: "transparent"
                                                border.color: clrAccent; border.width: 2; opacity: parent.parent.activeFocus ? 0.35 : 0.0
                                                scale: parent.parent.activeFocus ? 1.0 : 0.98
                                                Behavior on opacity { NumberAnimation { duration: 180; easing.type: Easing.OutQuad } }
                                                Behavior on scale { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
                                            }
                                        }
                                    }
                                }
                            }

                            // Gemini Ayarları
                            ColumnLayout {
                                Layout.fillWidth: true; spacing: 14
                                visible: appBackend.selectedEngine === "gemini"

                                RowLayout {
                                    Layout.fillWidth: true; spacing: 18
                                    ColumnLayout {
                                        Layout.fillWidth: true; spacing: 5
                                        Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("label_gemini_key", "Gemini API Key:"); color: clrTxt; font.bold: true; font.pixelSize: 13 }
                                        TextField {
                                            Layout.fillWidth: true; height: 40; text: appBackend.geminiApiKey; echoMode: TextInput.Password; placeholderText: "AIza..."
                                            onEditingFinished: appBackend.geminiApiKey = text
                                            background: Rectangle {
                                                radius: 10; color: clrInput
                                                border.color: parent.activeFocus ? clrAccent : clrCardBorder; border.width: 1
                                                Behavior on border.color { ColorAnimation { duration: 150 } }
                                                Rectangle {
                                                    anchors.fill: parent; anchors.margins: -3; radius: parent.radius + 2; color: "transparent"
                                                    border.color: clrAccent; border.width: 2; opacity: parent.parent.activeFocus ? 0.35 : 0.0
                                                    scale: parent.parent.activeFocus ? 1.0 : 0.98
                                                    Behavior on opacity { NumberAnimation { duration: 180; easing.type: Easing.OutQuad } }
                                                    Behavior on scale { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
                                                }
                                            }
                                        }
                                    }
                                    ColumnLayout {
                                        Layout.fillWidth: true; spacing: 5
                                        Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("label_gemini_model", "Model:"); color: clrTxt; font.bold: true; font.pixelSize: 13 }
                                        TextField {
                                            Layout.fillWidth: true; height: 40; text: appBackend.geminiModel; placeholderText: "gemini-2.0-flash"
                                            onEditingFinished: appBackend.geminiModel = text
                                            background: Rectangle {
                                                radius: 10; color: clrInput
                                                border.color: parent.activeFocus ? clrAccent : clrCardBorder; border.width: 1
                                                Behavior on border.color { ColorAnimation { duration: 150 } }
                                                Rectangle {
                                                    anchors.fill: parent; anchors.margins: -3; radius: parent.radius + 2; color: "transparent"
                                                    border.color: clrAccent; border.width: 2; opacity: parent.parent.activeFocus ? 0.35 : 0.0
                                                    scale: parent.parent.activeFocus ? 1.0 : 0.98
                                                    Behavior on opacity { NumberAnimation { duration: 180; easing.type: Easing.OutQuad } }
                                                    Behavior on scale { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
                                                }
                                            }
                                        }
                                    }
                                }

                                RowLayout {
                                    Layout.fillWidth: true; spacing: 18
                                    ColumnLayout {
                                        Layout.fillWidth: true; spacing: 5
                                        Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("label_gemini_safety", "Safety Filter Level:"); color: clrTxt; font.bold: true; font.pixelSize: 13 }
                                        ComboBox {
                                            id: settingsGeminiSafetyCombo
                                            Layout.fillWidth: true; height: 40
                                            function safetyModel() {
                                                appBackend.uiTrigger
                                                return [
                                                    { "id": "BLOCK_NONE", "name": appBackend.getTextWithDefault("gemini_safety_block_none", "BLOCK_NONE (Unrestricted / NSFW-Friendly - Recommended)") },
                                                    { "id": "BLOCK_ONLY_HIGH", "name": appBackend.getTextWithDefault("gemini_safety_only_high", "BLOCK_ONLY_HIGH (Filter High Risk Only)") },
                                                    { "id": "STANDARD", "name": appBackend.getTextWithDefault("gemini_safety_standard", "STANDARD (Google Default - Strict)") }
                                                ]
                                            }
                                            model: safetyModel()
                                            textRole: "name"; valueRole: "id"
                                            function syncSafety() {
                                                var val = appBackend.geminiSafetySettings || "BLOCK_NONE"
                                                var idx = settingsGeminiSafetyCombo.indexOfValue(val)
                                                if (idx >= 0) settingsGeminiSafetyCombo.currentIndex = idx
                                            }
                                            Component.onCompleted: syncSafety()
                                            Connections {
                                                target: appBackend
                                                function onGeminiSafetySettingsChanged() { settingsGeminiSafetyCombo.syncSafety() }
                                                function onUiTriggerChanged() { settingsGeminiSafetyCombo.syncSafety() }
                                            }
                                            onActivated: appBackend.geminiSafetySettings = currentValue
                                            background: Rectangle {
                                                radius: 10; color: clrInput; border.color: parent.hovered ? clrAccent : clrCardBorder; border.width: 1
                                                Behavior on border.color { ColorAnimation { duration: 150 } }
                                            }
                                            contentItem: Label { leftPadding: 14; text: settingsGeminiSafetyCombo.displayText; color: clrTxt; font.pixelSize: 12; verticalAlignment: Text.AlignVCenter }
                                            delegate: ItemDelegate {
                                                width: settingsGeminiSafetyCombo.width
                                                contentItem: Label { text: modelData.name; color: clrTxt; font.pixelSize: 12; leftPadding: 14 }
                                                background: Rectangle { color: hovered ? Qt.rgba(184, 243, 107, 0.12) : "transparent"; Behavior on color { ColorAnimation { duration: 120 } } }
                                            }
                                            popup: Popup { y: settingsGeminiSafetyCombo.height; width: settingsGeminiSafetyCombo.width; implicitHeight: Math.min(contentItem.implicitHeight, 220); padding: 4; contentItem: ListView { clip: true; implicitHeight: contentHeight; model: settingsGeminiSafetyCombo.delegateModel; ScrollBar.vertical: ScrollBar {} } background: Rectangle { color: clrCard; radius: 10; border.color: clrCardBorder; border.width: 1 } }
                                        }
                                    }
                                }
                            }


                            // AI Çeviri Modu (Translation Mode: Scene / JSON / XML) & Sahne Blok Boyutu
                            ColumnLayout {
                                Layout.fillWidth: true; spacing: 14
                                visible: appBackend.selectedEngine === "openai" || appBackend.selectedEngine === "deepseek" || appBackend.selectedEngine === "gemini" || appBackend.selectedEngine === "google"

                                RowLayout {
                                    Layout.fillWidth: true; spacing: 18

                                    // Çeviri Modu Seçimi
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        Layout.preferredWidth: appBackend.aiBatchFormat === "scene" ? 3 : 1
                                        spacing: 5

                                        Label {
                                            text: appBackend.uiTrigger, appBackend.getTextWithDefault("ai_mode_label", "Translation Mode:");
                                            color: clrTxt; font.bold: true; font.pixelSize: 13
                                        }

                                        ComboBox {
                                            id: aiBatchModeCombo
                                            Layout.fillWidth: true; height: 40
                                            function modeModel() {
                                                appBackend.uiTrigger
                                                return [
                                                    {"id": "scene", "name": appBackend.getTextWithDefault("ai_mode_scene", "Scene / Screenplay Mode (Context-Aware)")},
                                                    {"id": "json", "name": appBackend.getTextWithDefault("ai_mode_json", "Standard Structured Mode (JSON)")},
                                                    {"id": "xml", "name": appBackend.getTextWithDefault("ai_mode_xml", "Legacy Grouping Mode (XML)")},
                                                    {"id": "single", "name": appBackend.getTextWithDefault("ai_mode_single", "Single Line Mode (No Context)")}
                                                ]
                                            }
                                            model: modeModel()
                                            textRole: "name"; valueRole: "id"
                                            Component.onCompleted: currentIndex = indexOfValue(appBackend.aiBatchFormat || "scene")
                                            onActivated: appBackend.aiBatchFormat = currentValue
                                            background: Rectangle { radius: 10; color: clrInput; border.color: parent.hovered ? clrAccent : clrCardBorder; border.width: 1 }
                                            contentItem: Label { leftPadding: 14; rightPadding: 14; text: aiBatchModeCombo.displayText; color: clrTxt; font.pixelSize: 12; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
                                            delegate: ItemDelegate {
                                                width: aiBatchModeCombo.width
                                                contentItem: Label { text: modelData.name; color: clrTxt; font.pixelSize: 12; leftPadding: 14; elide: Text.ElideRight }
                                                background: Rectangle { color: hovered ? Qt.rgba(184, 243, 107, 0.12) : "transparent" }
                                            }
                                            popup: Popup {
                                                y: aiBatchModeCombo.height; width: aiBatchModeCombo.width
                                                implicitHeight: Math.min(contentItem.implicitHeight, 200)
                                                padding: 4
                                                contentItem: ListView { clip: true; implicitHeight: contentHeight; model: aiBatchModeCombo.delegateModel; ScrollBar.vertical: ScrollBar {} }
                                                background: Rectangle { color: clrCard; radius: 10; border.color: clrCardBorder; border.width: 1 }
                                            }
                                        }
                                    }

                                    // Sahne Blok Boyutu (Scene Block Size) - Sadece Sahne Modunda Aktif
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        Layout.preferredWidth: 2
                                        spacing: 6
                                        visible: appBackend.aiBatchFormat === "scene"

                                        Label {
                                            text: appBackend.uiTrigger, appBackend.getTextWithDefault("ai_scene_size_label", "Scene Block Size (Lines)") + ": " + Math.round(aiSceneSlider.value)
                                            color: clrTxt; font.bold: true; font.pixelSize: 13
                                        }

                                        Slider {
                                            id: aiSceneSlider
                                            Layout.fillWidth: true
                                            from: 5; to: 50; stepSize: 5
                                            value: appBackend.aiSceneBatchSize
                                            onMoved: appBackend.aiSceneBatchSize = Math.round(value)
                                        }
                                    }
                                }

                                // Seçili Moda Göre Canlı Açıklama / Rehber
                                Label {
                                    Layout.fillWidth: true
                                    wrapMode: Text.WordWrap
                                    font.pixelSize: 12
                                    color: clrTxt2
                                    text: {
                                        appBackend.uiTrigger
                                        if (appBackend.aiBatchFormat === "scene") {
                                            return appBackend.getTextWithDefault("ai_mode_scene_desc", "💡 Diyalogları senaryo akışı halinde iletir. Karakter hitaplarını, cinsiyet uyumunu ve bağlamı en iyi koruyan moddur (Görsel romanlar için önerilen).")
                                        } else if (appBackend.aiBatchFormat === "single") {
                                            return appBackend.getTextWithDefault("ai_mode_single_desc", "💡 Her satırı ayrı istek olarak gönderir; komşu satır ve konuşmacı bağlamı iletilmez. Toplu istek biçimini bozan modeller için önerilir — sonuç daha tutarlı olur. Daha fazla istek, daha yavaş ama daha az format hatası.")
                                        } else if (appBackend.aiBatchFormat === "json") {
                                            return appBackend.getTextWithDefault("ai_mode_json_desc", "💡 Metinleri anahtar-değer çifti olarak iletir. Sıfır satır kayması ve katı veri bütünlüğü sağlar; menü ve sistem metinleri için idealdir.")
                                        } else {
                                            return appBackend.getTextWithDefault("ai_mode_xml_desc", "💡 Metinleri XML etiketleriyle paketler. JSON üretmekte zorlanan küçük veya eski modeller için en güvenli seçenektir.")
                                        }
                                    }
                                }
                            }


                            // LibreTranslate Ayarları
                            ColumnLayout {
                                Layout.fillWidth: true; spacing: 14
                                visible: appBackend.selectedEngine === "libretranslate"

                                RowLayout {
                                    Layout.fillWidth: true; spacing: 18
                                    ColumnLayout {
                                        Layout.fillWidth: true; spacing: 5
                                        Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("libretranslate_url_label", "LibreTranslate Server URL:"); color: clrTxt; font.bold: true; font.pixelSize: 13 }
                                        TextField {
                                            Layout.fillWidth: true; height: 40; text: appBackend.libretranslateUrl; placeholderText: "http://localhost:5000"
                                            onEditingFinished: appBackend.libretranslateUrl = text
                                            background: Rectangle { radius: 10; color: clrInput; border.color: clrCardBorder; border.width: 1 }
                                        }
                                    }
                                    ColumnLayout {
                                        Layout.fillWidth: true; spacing: 5
                                        Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("libretranslate_api_key_label", "LibreTranslate API Key (Optional):"); color: clrTxt; font.bold: true; font.pixelSize: 13 }
                                        TextField {
                                            Layout.fillWidth: true; height: 40; text: appBackend.libretranslateApiKey; echoMode: TextInput.Password
                                            onEditingFinished: appBackend.libretranslateApiKey = text
                                            background: Rectangle { radius: 10; color: clrInput; border.color: clrCardBorder; border.width: 1 }
                                        }
                                    }
                                }
                            }

                        }
                    }

                    // GELİŞMİŞ YAPAY ZEKA PARAMETRELERİ (TUNING & SYSTEM PROMPT) KARTI
                    Rectangle {
                        id: cardAiTuning
                        visible: pageSettings.settingsSubTab === 1
                        Layout.fillWidth: true
                        Layout.preferredHeight: aiTuningCol.implicitHeight + 44
                        radius: 16; color: clrCard; border.color: clrCardBorder; border.width: 1
                        Behavior on Layout.preferredHeight { NumberAnimation { duration: 200 } }

                        ColumnLayout {
                            id: aiTuningCol
                            anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                            anchors.margins: 22; spacing: 18

                            Label { text: appBackend.uiTrigger, "⚡ " + appBackend.getTextWithDefault("ai_tuning_title", "Advanced AI Tuning & System Prompt"); font.pixelSize: 16; font.bold: true; color: clrAccent }

                            // Satır 1: Temperature & Max Tokens
                            RowLayout {
                                Layout.fillWidth: true; spacing: 24
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 6
                                    Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("ai_temp_label", "AI Temperature") + ": " + aiTempSlider.value.toFixed(2); color: clrTxt; font.bold: true; font.pixelSize: 13 }
                                    Slider { id: aiTempSlider; Layout.fillWidth: true; from: 0.0; to: 1.0; stepSize: 0.05; value: appBackend.aiTemperature; onMoved: appBackend.aiTemperature = value }
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 6
                                    Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("ai_tokens_label", "Max Tokens") + ": " + Math.round(aiTokensSlider.value); color: clrTxt; font.bold: true; font.pixelSize: 13 }
                                    Slider { id: aiTokensSlider; Layout.fillWidth: true; from: 256; to: 8192; stepSize: 256; value: appBackend.aiMaxTokens; onMoved: appBackend.aiMaxTokens = value }
                                }
                            }

                            // Satır 2: AI Timeout & AI Batch Size
                            RowLayout {
                                Layout.fillWidth: true; spacing: 24
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 6
                                    Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("ai_timeout_label", "AI Timeout") + ": " + Math.round(aiTimeoutSlider.value) + "s"; color: clrTxt; font.bold: true; font.pixelSize: 13 }
                                    Slider { id: aiTimeoutSlider; Layout.fillWidth: true; from: 10; to: 300; stepSize: 10; value: appBackend.aiTimeout; onMoved: appBackend.aiTimeout = value }
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 6
                                    Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("ai_batch_label", "AI Batch Size") + ": " + Math.round(aiBatchSlider.value); color: clrTxt; font.bold: true; font.pixelSize: 13 }
                                    Slider { id: aiBatchSlider; Layout.fillWidth: true; from: 1; to: 50; stepSize: 1; value: appBackend.aiBatchSize; onMoved: appBackend.aiBatchSize = value }
                                }
                            }

                            // Satır 3: AI Retry Count & AI Concurrency
                            RowLayout {
                                Layout.fillWidth: true; spacing: 24
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 6
                                    Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("ai_retry_label", "AI Retry Count") + ": " + Math.round(aiRetrySlider.value); color: clrTxt; font.bold: true; font.pixelSize: 13 }
                                    Slider { id: aiRetrySlider; Layout.fillWidth: true; from: 1; to: 5; stepSize: 1; value: appBackend.aiRetryCount; onMoved: appBackend.aiRetryCount = value }
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 6
                                    Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("ai_concurrency_label", "AI Concurrency") + ": " + Math.round(aiConcSlider.value); color: clrTxt; font.bold: true; font.pixelSize: 13 }
                                    Slider { id: aiConcSlider; Layout.fillWidth: true; from: 1; to: 10; stepSize: 1; value: appBackend.aiConcurrency; onMoved: appBackend.aiConcurrency = value }
                                }
                            }

                            // Satır 4: Custom System Prompt (Çok Satırlı TextArea)
                            ColumnLayout {
                                Layout.fillWidth: true; spacing: 6
                                Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("ai_prompt_label", "Custom System Prompt (Optional instructions for AI):"); color: clrTxt; font.bold: true; font.pixelSize: 13 }
                                ScrollView {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 96
                                    clip: true
                                    ScrollBar.vertical: ScrollBar {}
                                    TextArea {
                                        id: aiPromptField
                                        text: appBackend.aiCustomSystemPrompt
                                        placeholderText: appBackend.uiTrigger, appBackend.getTextWithDefault("ai_prompt_placeholder", "Translate the following Ren'Py visual novel dialogue accurately while keeping tags...")
                                        wrapMode: TextEdit.Wrap
                                        onEditingFinished: appBackend.aiCustomSystemPrompt = text
                                        font.pixelSize: 12; color: clrTxt
                                        selectByMouse: true
                                        background: Rectangle {
                                            radius: 10
                                            color: clrInput
                                            border.color: aiPromptField.activeFocus ? clrAccent : clrCardBorder
                                            border.width: 1
                                            Behavior on border.color { ColorAnimation { duration: 150 } }

                                            // Focus Ring Glow
                                            Rectangle {
                                                anchors.fill: parent
                                                anchors.margins: -3
                                                radius: parent.radius + 2
                                                color: "transparent"
                                                border.color: clrAccent
                                                border.width: 2
                                                opacity: aiPromptField.activeFocus ? 0.35 : 0.0
                                                scale: aiPromptField.activeFocus ? 1.0 : 0.98
                                                Behavior on opacity { NumberAnimation { duration: 180; easing.type: Easing.OutQuad } }
                                                Behavior on scale { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
                                            }
                                        }
                                    }
                                }

                            }
                        }
                    }

                    Item { height: 24 }
                }
            }
        }

            // ═════════════════════════════════════════════════════════════
            // SEKME 2: LOG CONSOLE & STUDIO TERMINAL
            // ═════════════════════════════════════════════════════════════
            Item {
                id: pageLogs
                visible: navIndex === 2
                Layout.fillWidth: true
                Layout.fillHeight: true

                property string selectedLevel: "ALL"
                property string logSearchQuery: ""

                transform: Translate { id: animTrLogs; y: 14 }
                opacity: 0.0
                ParallelAnimation {
                    id: animEntranceLogs
                    NumberAnimation { target: animTrLogs; property: "y"; from: 14; to: 0; duration: 220; easing.type: Easing.OutCubic }
                    NumberAnimation { target: pageLogs; property: "opacity"; from: 0.0; to: 1.0; duration: 180; easing.type: Easing.OutQuad }
                }
                onVisibleChanged: if (visible) animEntranceLogs.restart()

                // Sabit Sticky Terminal Araç Çubuğu
                Rectangle {
                    id: logStickyHeader
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    height: 104
                    z: 10
                    color: clrBg
                    border.color: clrCardBorder
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 10

                        // Üst Satır: Başlık, Sayaç ve Eylemler
                        RowLayout {
                            Layout.fillWidth: true; spacing: 12
                            Rectangle {
                                width: 34; height: 34; radius: 10
                                color: Qt.rgba(184, 243, 107, 0.12)
                                border.color: Qt.rgba(184, 243, 107, 0.3); border.width: 1
                                Label { anchors.centerIn: parent; text: "⚡"; font.pixelSize: 18 }
                            }
                            ColumnLayout {
                                spacing: 1
                                Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("ln_diag_title", "Diagnóstico de ejecución"); font.pixelSize: 17; font.bold: true; color: clrTxt }
                                Label { text: appBackend.uiTrigger, logModel.count + " " + appBackend.getTextWithDefault("logs_count_label", "events recorded in session."); font.pixelSize: 11; color: clrTxt2 }
                            }
                            Item { Layout.fillWidth: true }

                            Button {
                                height: 34; text: appBackend.uiTrigger, "📋 " + appBackend.getTextWithDefault("copy_log", "Copy Log")
                                onClicked: {
                                    var lines = []
                                    for (var i = 0; i < logModel.count; i++) {
                                        var item = logModel.get(i)
                                        lines.push(item.ts + " [" + item.level.toUpperCase() + "] " + item.message)
                                    }
                                    appBackend.copyToClipboard(lines.join("\n"))
                                    showToast(appBackend.getTextWithDefault("log_copied_clipboard", "Log copied to clipboard!"), "info")
                                }
                                background: Rectangle { radius: 10; color: parent.hovered ? clrCardHover : clrInput; border.color: clrCardBorder; border.width: 1 }
                                contentItem: Label { text: parent.text; color: clrTxt; font.pixelSize: 11; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                            }
                            Button {
                                height: 34; text: appBackend.uiTrigger, "🗑 " + appBackend.getTextWithDefault("clear_log", "Clear")
                                onClicked: logModel.clear()
                                background: Rectangle { radius: 10; color: parent.hovered ? "#3B1111" : clrInput; border.color: clrCardBorder; border.width: 1 }
                                contentItem: Label { text: parent.text; color: clrError; font.pixelSize: 11; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                            }
                        }

                        // Alt Satır: Seviye Filtreleri (Segments) + Canlı Arama
                        RowLayout {
                            Layout.fillWidth: true; spacing: 12

                            // Segmented Level Filter Bar
                            Rectangle {
                                height: 32; radius: 10
                                color: clrCard; border.color: clrCardBorder; border.width: 1
                                Layout.preferredWidth: filterRow.implicitWidth + 8

                                RowLayout {
                                    id: filterRow
                                    anchors.centerIn: parent
                                    spacing: 4

                                    Repeater {
                                        model: [
                                            { label: "ALL", key: "ALL", color: clrTxt },
                                            { label: "INFO", key: "INFO", color: clrAccent },
                                            { label: "WARN", key: "WARNING", color: clrWarn },
                                            { label: "ERROR", key: "ERROR", color: clrError }
                                        ]
                                        delegate: Rectangle {
                                            width: 60; height: 26; radius: 6
                                            color: pageLogs.selectedLevel === modelData.key ? Qt.rgba(modelData.color.r, modelData.color.g, modelData.color.b, 0.18) : "transparent"
                                            border.color: pageLogs.selectedLevel === modelData.key ? modelData.color : "transparent"; border.width: 1
                                            Label {
                                                anchors.centerIn: parent
                                                text: modelData.label
                                                font.pixelSize: 10; font.bold: pageLogs.selectedLevel === modelData.key
                                                color: pageLogs.selectedLevel === modelData.key ? modelData.color : clrTxt2
                                            }
                                            MouseArea {
                                                anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                                onClicked: pageLogs.selectedLevel = modelData.key
                                            }
                                        }
                                    }
                                }
                            }

                            // Canlı Arama Kutusu
                            Rectangle {
                                Layout.fillWidth: true; height: 32; radius: 10
                                color: clrInput; border.color: clrCardBorder; border.width: 1
                                RowLayout {
                                    anchors.fill: parent; anchors.leftMargin: 10; anchors.rightMargin: 10; spacing: 6
                                    Label { text: "🔍"; font.pixelSize: 11; color: clrTxtDim }
                                    TextInput {
                                        id: logSearchInput
                                        Layout.fillWidth: true
                                        font.pixelSize: 11; color: clrTxt
                                        clip: true
                                        Text {
                                            anchors.fill: parent
                                            verticalAlignment: Text.AlignVCenter
                                            text: appBackend.uiTrigger, appBackend.getTextWithDefault("logs_search_placeholder", "Loglarda filtrele veya anahtar kelime ara...")
                                            color: clrTxtDim; font.pixelSize: 11
                                            visible: !logSearchInput.text && !logSearchInput.activeFocus
                                        }
                                        onTextChanged: pageLogs.logSearchQuery = text.trim().toLowerCase()
                                    }
                                    Button {
                                        visible: logSearchInput.text.length > 0
                                        width: 18; height: 18; text: "✕"
                                        onClicked: { logSearchInput.text = ""; pageLogs.logSearchQuery = "" }
                                        background: Item {}
                                        contentItem: Label { text: "✕"; color: clrTxtDim; font.pixelSize: 10; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                    }
                                }
                            }
                        }
                    }
                }

                // Konsol Çıktı Terminali (Doğrudan ListView — Nested Scroll Yok!)
                Rectangle {
                    anchors.top: logStickyHeader.bottom
                    anchors.bottom: parent.bottom
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.margins: 14
                    radius: 14
                    color: Qt.darker(clrCard, 1.25)
                    border.color: clrCardBorder
                    border.width: 1

                    ListView {
                        id: logConsoleListView
                        anchors.fill: parent
                        anchors.margins: 12
                        clip: true
                        model: logModel
                        spacing: 4
                        ScrollBar.vertical: ScrollBar {}

                        // Otomatik aşağı kaydırma
                        onCountChanged: {
                            if (logConsoleListView.atYEnd || logModel.count < 10) {
                                logConsoleListView.positionViewAtEnd()
                            }
                        }

                        delegate: Item {
                            id: logItemDelegate
                            property bool matchesLevel: pageLogs.selectedLevel === "ALL" || (model.level || "").toUpperCase() === pageLogs.selectedLevel
                            property bool matchesSearch: pageLogs.logSearchQuery.length === 0 || (model.message || "").toLowerCase().indexOf(pageLogs.logSearchQuery) !== -1
                            property bool isVisibleInFilter: matchesLevel && matchesSearch

                            visible: isVisibleInFilter
                            width: logConsoleListView.width
                            height: isVisibleInFilter ? logRowLayout.implicitHeight + 4 : 0

                            RowLayout {
                                id: logRowLayout
                                anchors.fill: parent
                                spacing: 10

                                Label {
                                    text: model.ts || ""
                                    color: clrTxtDim; font.pixelSize: 11; font.family: "Consolas, 'Courier New', monospace"
                                    Layout.preferredWidth: 65
                                }
                                Label {
                                    text: logPrefix(model.level)
                                    color: logColor(model.level)
                                    font.bold: true; font.pixelSize: 11; font.family: "Consolas, 'Courier New', monospace"
                                    Layout.preferredWidth: 55
                                }
                                Label {
                                    text: model.message || ""
                                    color: logColor(model.level)
                                    font.pixelSize: 11; font.family: "Consolas, 'Courier New', monospace"
                                    Layout.fillWidth: true
                                    wrapMode: Text.Wrap
                                }
                            }
                        }
                    }
                }
            }

        // ═════════════════════════════════════════════════════════════
        // SEKME 3: TOOLBOX (GELİŞMİŞ REN'PY ARAÇ KUTUSU)
        // ═════════════════════════════════════════════════════════════
        ScrollView {
            id: viewToolbox
            visible: navIndex === 3
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            contentWidth: availableWidth
            contentHeight: toolboxContent.implicitHeight + (root.responsivePageMargin * 2)
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
            ScrollBar.vertical.policy: root.needsPageScroll(viewToolbox.contentHeight, viewToolbox.availableHeight)
                                           ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff

            transform: Translate { id: animTrToolbox; y: 14 }
            opacity: 0.0
            ParallelAnimation {
                id: animEntranceToolbox
                NumberAnimation { target: animTrToolbox; property: "y"; from: 14; to: 0; duration: 220; easing.type: Easing.OutCubic }
                NumberAnimation { target: viewToolbox; property: "opacity"; from: 0.0; to: 1.0; duration: 180; easing.type: Easing.OutQuad }
            }
            onVisibleChanged: if (visible) animEntranceToolbox.restart()

            ColumnLayout {
                id: toolboxContent
                y: root.responsivePageMargin
                width: Math.max(0, Math.min(viewToolbox.availableWidth - (root.responsivePageMargin * 2), 1180))
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: root.responsiveSectionSpacing

                // Başlık Alanı
                RowLayout {
                    Layout.fillWidth: true; spacing: 14
                    Rectangle {
                        width: 42; height: 42; radius: 12
                        color: Qt.rgba(184, 243, 107, 0.12)
                        border.color: Qt.rgba(184, 243, 107, 0.3); border.width: 1
                        Label { anchors.centerIn: parent; text: "🛠️"; font.pixelSize: 22 }
                    }
                    ColumnLayout {
                        spacing: 2
                        Label {
                            text: appBackend.uiTrigger, appBackend.getTextWithDefault("ln_tools_title", "Utilidades del proyecto")
                            font.pixelSize: root.fitFirstDesktop ? 18 : 20
                            font.bold: true; color: clrTxt
                        }
                        Label {
                            text: appBackend.uiTrigger, appBackend.getTextWithDefault("ln_tools_desc", "Operaciones auxiliares para comprobar, adaptar y reparar contenido Ren'Py sin mezclarlo con el flujo principal.")
                            font.pixelSize: root.compactHeight ? 11 : 12; color: clrTxt2; wrapMode: Text.Wrap; Layout.fillWidth: true
                        }
                    }
                }

                // 2-Sütunlu Dengeli Araç Kutusu Izgarası
                GridLayout {
                    Layout.fillWidth: true
                    // Two columns on normal desktop widths; narrow windows fall back
                    // to one column and remain fully accessible through scrolling.
                    columns: viewToolbox.availableWidth < 900 ? 1 : 2
                    columnSpacing: root.compactWidth ? 12 : 18
                    rowSpacing: root.compactHeight ? 12 : 18

                    // ── KART 1: FONT DEĞİŞTİRİCİ VE ENJEKTÖR ─────────────────────
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: fontCardCol.implicitHeight + (root.compactHeight ? 24 : 36)
                        radius: 18; color: clrCard; border.color: clrCardBorder; border.width: 1

                        ColumnLayout {
                            id: fontCardCol
                            anchors.fill: parent
                            anchors.margins: root.responsiveCardPadding
                            spacing: root.responsiveCardSpacing

                            RowLayout {
                                spacing: 12; Layout.fillWidth: true
                                Rectangle {
                                    width: 38; height: root.responsiveButtonHeight; radius: 10; color: Qt.rgba(184, 243, 107, 0.1)
                                    border.color: Qt.rgba(184, 243, 107, 0.3); border.width: 1
                                    Label { anchors.centerIn: parent; text: "🔤"; font.pixelSize: 18 }
                                }
                                ColumnLayout {
                                    spacing: 1; Layout.fillWidth: true
                                    Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("tool_font_title", "Font Değiştirici ve Enjektör"); font.pixelSize: 15; font.bold: true; color: clrTxt }
                                    Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("ln_tool_font_subtitle", "OpenType / TrueType auto-injector"); font.pixelSize: 11; color: clrTxtDim }
                                }
                                Rectangle {
                                    radius: 6; color: Qt.rgba(184, 243, 107, 0.12)
                                    Layout.preferredHeight: 20; Layout.preferredWidth: 54
                                    Label { anchors.centerIn: parent; text: appBackend.uiTrigger, appBackend.getTextWithDefault("ln_tool_font_badge", "FONT"); font.pixelSize: 9; font.bold: true; color: clrAccent }
                                }
                            }

                            Label {
                                text: appBackend.uiTrigger, appBackend.getTextWithDefault("tool_font_desc", "Japonca/İngilizce oyun fontlarını Türkçe karakter destekli evrensel fontlarla otomatik değiştirerek kare kare yazı hatasını kökünden çözer.")
                                font.pixelSize: root.compactHeight ? 11 : 12; color: clrTxt2; wrapMode: Text.Wrap; Layout.fillWidth: true
                            }

                            RowLayout {
                                Layout.fillWidth: true; spacing: 10
                                Button {
                                    Layout.fillWidth: true; height: root.responsiveButtonHeight
                                    text: appBackend.uiTrigger, "⚡ " + appBackend.getTextWithDefault("btn_run_font", "Kontrol Et")
                                    onClicked: appBackend.runToolFontHelper()
                                    background: Rectangle {
                                        radius: 10; color: parent.hovered ? clrCardHover : clrInput
                                        border.color: parent.hovered ? clrAccent : clrCardBorder; border.width: 1
                                    }
                                    contentItem: Label { text: parent.text; color: clrAccent; font.pixelSize: 12; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                }
                                Button {
                                    Layout.fillWidth: true; height: root.responsiveButtonHeight
                                    text: appBackend.uiTrigger, "📥 " + appBackend.getTextWithDefault("btn_font_inject", "Enjekte Et")
                                    onClicked: appBackend.runToolFontInject()
                                    background: Rectangle {
                                        radius: 10; color: parent.hovered ? clrCardHover : clrInput
                                        border.color: parent.hovered ? clrSuccess : clrCardBorder; border.width: 1
                                    }
                                    contentItem: Label { text: parent.text; color: clrSuccess; font.pixelSize: 12; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                }
                            }
                        }
                    }

                    // ── KART 2: REN'PY HATA DOKTORU (LINT) ──────────────────────
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: lintCardCol.implicitHeight + (root.compactHeight ? 24 : 36)
                        radius: 18; color: clrCard; border.color: clrCardBorder; border.width: 1

                        ColumnLayout {
                            id: lintCardCol
                            anchors.fill: parent
                            anchors.margins: root.responsiveCardPadding
                            spacing: root.responsiveCardSpacing

                            RowLayout {
                                spacing: 12; Layout.fillWidth: true
                                Rectangle {
                                    width: 38; height: root.responsiveButtonHeight; radius: 10; color: Qt.rgba(168, 85, 247, 0.1)
                                    border.color: Qt.rgba(168, 85, 247, 0.3); border.width: 1
                                    Label { anchors.centerIn: parent; text: "🩺"; font.pixelSize: 18 }
                                }
                                ColumnLayout {
                                    spacing: 1; Layout.fillWidth: true
                                    Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("tool_lint_title", "Ren'Py Hata Doktoru"); font.pixelSize: 15; font.bold: true; color: clrTxt }
                                    Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("ln_tool_lint_subtitle", "Syntax & indentation guard"); font.pixelSize: 11; color: clrTxtDim }
                                }
                                Rectangle {
                                    radius: 6; color: Qt.rgba(168, 85, 247, 0.15)
                                    Layout.preferredHeight: 20; Layout.preferredWidth: 48
                                    Label { anchors.centerIn: parent; text: appBackend.uiTrigger, appBackend.getTextWithDefault("ln_tool_lint_badge", "LINT"); font.pixelSize: 9; font.bold: true; color: clrPurple }
                                }
                            }

                            Label {
                                text: appBackend.uiTrigger, appBackend.getTextWithDefault("tool_lint_desc", "Çeviri sonrasında bozulan satır girintularını, eksik tırnakları ve değişken etiketlerini tarayıp oyunun açılırken çökmesini önler.")
                                font.pixelSize: root.compactHeight ? 11 : 12; color: clrTxt2; wrapMode: Text.Wrap; Layout.fillWidth: true
                            }

                            Button {
                                Layout.fillWidth: true; height: root.responsiveButtonHeight
                                text: appBackend.uiTrigger, "🩺 " + appBackend.getTextWithDefault("btn_run_lint", "Hata Taramasını Başlat")
                                onClicked: appBackend.runToolRenpyLint()
                                background: Rectangle {
                                    radius: 10; color: parent.hovered ? clrCardHover : clrInput
                                    border.color: parent.hovered ? clrPurple : clrCardBorder; border.width: 1
                                }
                                contentItem: Label { text: parent.text; color: clrPurple; font.pixelSize: 12; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                            }
                        }
                    }

                    // ── KART 3: TERİM SÖZLÜĞÜ ÇIKARICI (GLOSSARY) ───────────────
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: glossCardCol.implicitHeight + (root.compactHeight ? 24 : 36)
                        radius: 18; color: clrCard; border.color: clrCardBorder; border.width: 1

                        ColumnLayout {
                            id: glossCardCol
                            anchors.fill: parent
                            anchors.margins: root.responsiveCardPadding
                            spacing: root.responsiveCardSpacing

                            RowLayout {
                                spacing: 12; Layout.fillWidth: true
                                Rectangle {
                                    width: 38; height: root.responsiveButtonHeight; radius: 10; color: Qt.rgba(16, 185, 129, 0.1)
                                    border.color: Qt.rgba(16, 185, 129, 0.3); border.width: 1
                                    Label { anchors.centerIn: parent; text: "📚"; font.pixelSize: 18 }
                                }
                                ColumnLayout {
                                    spacing: 1; Layout.fillWidth: true
                                    Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("tool_glossary_title", "Terim Sözlüğü Çıkarıcı"); font.pixelSize: 15; font.bold: true; color: clrTxt }
                                    Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("ln_tool_glossary_subtitle", "Entity & name scanner"); font.pixelSize: 11; color: clrTxtDim }
                                }
                                Rectangle {
                                    radius: 6; color: Qt.rgba(16, 185, 129, 0.15)
                                    Layout.preferredHeight: 20; Layout.preferredWidth: 62
                                    Label { anchors.centerIn: parent; text: appBackend.uiTrigger, appBackend.getTextWithDefault("ln_tool_glossary_badge", "GLOSSARY"); font.pixelSize: 9; font.bold: true; color: clrSuccess }
                                }
                            }

                            Label {
                                text: appBackend.uiTrigger, appBackend.getTextWithDefault("tool_glossary_desc", "Oyun içindeki özel isimleri, karakter adlarını ve krallık terimlerini tarayıp otomatik olarak glossary.json dosyasına aktararak tutarlılık sağlar.")
                                font.pixelSize: root.compactHeight ? 11 : 12; color: clrTxt2; wrapMode: Text.Wrap; Layout.fillWidth: true
                            }

                            Button {
                                Layout.fillWidth: true; height: root.responsiveButtonHeight
                                text: appBackend.uiTrigger, "📚 " + appBackend.getTextWithDefault("btn_run_glossary", "Terim Sözlüğünü Çıkar")
                                onClicked: appBackend.runToolGlossaryExtractor()
                                background: Rectangle {
                                    radius: 10; color: parent.hovered ? clrCardHover : clrInput
                                    border.color: parent.hovered ? clrSuccess : clrCardBorder; border.width: 1
                                }
                                contentItem: Label { text: parent.text; color: clrSuccess; font.pixelSize: 12; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                            }
                        }
                    }

                    // ── KART: DİL ETKİNLEŞTİRME (zzz_<lang>_language.rpy) ───────
                    // Ren'Py does not list tl/ folders by itself: this writes (or
                    // removes) the file that starts the game in a translated language.
                    Rectangle {
                        id: langActivateCard
                        Layout.fillWidth: true
                        Layout.preferredHeight: langActCol.implicitHeight + (root.compactHeight ? 24 : 36)
                        radius: 18; color: clrCard; border.color: clrCardBorder; border.width: 1

                        property var tlLangs: []
                        function refreshLangs() {
                            tlLangs = appBackend.toolListTlLanguages()
                            var pre = appBackend.toolDefaultTlLanguage()
                            var idx = tlLangs.indexOf(pre)
                            langActCombo.currentIndex = idx >= 0 ? idx : (tlLangs.length > 0 ? 0 : -1)
                        }
                        Connections {
                            target: viewToolbox
                            function onVisibleChanged() { if (viewToolbox.visible) langActivateCard.refreshLangs() }
                        }
                        Component.onCompleted: refreshLangs()

                        ColumnLayout {
                            id: langActCol
                            anchors.fill: parent
                            anchors.margins: root.responsiveCardPadding
                            spacing: root.responsiveCardSpacing

                            RowLayout {
                                spacing: 12; Layout.fillWidth: true
                                Rectangle {
                                    width: 38; height: root.responsiveButtonHeight; radius: 10; color: Qt.rgba(184, 243, 107, 0.1)
                                    border.color: Qt.rgba(184, 243, 107, 0.3); border.width: 1
                                    Label { anchors.centerIn: parent; text: "🏳️"; font.pixelSize: 18 }
                                }
                                ColumnLayout {
                                    spacing: 1; Layout.fillWidth: true
                                    Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("tool_lang_activate_title", "Native Language Menu"); font.pixelSize: 15; font.bold: true; color: clrTxt }
                                    Label { text: "zzz_linguanova_language_menu.rpy"; font.pixelSize: 11; color: clrTxtDim }
                                }
                                Rectangle {
                                    radius: 6; color: Qt.rgba(184, 243, 107, 0.15)
                                    Layout.preferredHeight: 20; Layout.preferredWidth: 48
                                    Label { anchors.centerIn: parent; text: appBackend.uiTrigger, appBackend.getTextWithDefault("ln_tool_lang_badge", "LANG"); font.pixelSize: 9; font.bold: true; color: clrAccent }
                                }
                            }

                            Label {
                                text: appBackend.uiTrigger, appBackend.getTextWithDefault("tool_lang_activate_desc", "LinguaNova scans the game's existing Language(...) selector and, when it can do so safely, adds the selected translation inside that native menu without forcing startup language.")
                                font.pixelSize: root.compactHeight ? 11 : 12; color: clrTxt2; wrapMode: Text.Wrap; Layout.fillWidth: true
                            }

                            RowLayout {
                                Layout.fillWidth: true; spacing: 8
                                ComboBox {
                                    id: langActCombo
                                    objectName: "toolLangActivateCombo"
                                    Layout.fillWidth: true; height: root.responsiveButtonHeight
                                    model: langActivateCard.tlLangs
                                    enabled: langActivateCard.tlLangs.length > 0
                                    displayText: langActivateCard.tlLangs.length > 0 ? currentText
                                                 : (appBackend.uiTrigger, appBackend.getTextWithDefault("tool_lang_no_tl", "No translation folders found in game/tl. Translate the game first."))
                                    background: Rectangle { radius: 10; color: clrInput; border.color: parent.hovered ? clrAccent : clrCardBorder; border.width: 1 }
                                    contentItem: Label {
                                        leftPadding: 14; rightPadding: 30
                                        text: langActCombo.displayText; elide: Text.ElideRight
                                        color: langActivateCard.tlLangs.length > 0 ? clrTxt : clrTxtDim
                                        font.pixelSize: 12; verticalAlignment: Text.AlignVCenter
                                    }
                                    delegate: ItemDelegate {
                                        width: langActCombo.width
                                        contentItem: Label { text: modelData; color: clrTxt; font.pixelSize: 12; leftPadding: 14; elide: Text.ElideRight }
                                        background: Rectangle { color: hovered ? Qt.rgba(184, 243, 107, 0.12) : "transparent" }
                                    }
                                    popup: Popup {
                                        y: langActCombo.height; width: langActCombo.width
                                        implicitHeight: Math.min(contentItem.implicitHeight, 220); padding: 4
                                        contentItem: ListView { clip: true; implicitHeight: contentHeight; model: langActCombo.delegateModel; ScrollBar.vertical: ScrollBar {} }
                                        background: Rectangle { color: clrCard; radius: 10; border.color: clrCardBorder; border.width: 1 }
                                    }
                                }
                                // Rescan game/tl (e.g. after translating another language)
                                Button {
                                    id: btnRefreshTlLangs
                                    Layout.preferredWidth: 38; Layout.preferredHeight: root.responsiveButtonHeight
                                    onClicked: langActivateCard.refreshLangs()
                                    ToolTip.visible: hovered
                                    ToolTip.delay: 250
                                    ToolTip.text: appBackend.uiTrigger, appBackend.getTextWithDefault("tool_lang_refresh", "Rescan the game's tl/ folder")
                                    background: Rectangle {
                                        radius: 10; color: btnRefreshTlLangs.hovered ? clrCardHover : clrInput
                                        border.color: btnRefreshTlLangs.hovered ? clrAccent : clrCardBorder; border.width: 1
                                    }
                                    contentItem: Label {
                                        text: "⟳"; color: btnRefreshTlLangs.hovered ? clrAccent : clrTxt2
                                        font.pixelSize: 17; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                                    }
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true; spacing: 8
                                Button {
                                    Layout.fillWidth: true; height: root.responsiveButtonHeight
                                    enabled: langActivateCard.tlLangs.length > 0
                                    text: appBackend.uiTrigger, "🏳️ " + appBackend.getTextWithDefault("btn_activate_language", "Integrate into game menu")
                                    onClicked: appBackend.runToolActivateLanguage(langActCombo.currentText)
                                    background: Rectangle {
                                        radius: 10; color: parent.hovered ? clrCardHover : clrInput
                                        border.color: parent.hovered ? clrAccent : clrCardBorder; border.width: 1
                                    }
                                    contentItem: Label { text: parent.text; color: clrAccent; font.pixelSize: 12; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
                                }
                                Button {
                                    Layout.fillWidth: true; height: root.responsiveButtonHeight
                                    text: appBackend.uiTrigger, appBackend.getTextWithDefault("btn_remove_language_activation", "Remove menu integration")
                                    onClicked: appBackend.runToolRemoveLanguageActivation()
                                    background: Rectangle {
                                        radius: 10; color: parent.hovered ? clrCardHover : clrInput
                                        border.color: parent.hovered ? clrError : clrCardBorder; border.width: 1
                                    }
                                    contentItem: Label { text: parent.text; color: clrTxt2; font.pixelSize: 12; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
                                }
                            }
                        }
                    }

                    // ── KART 4: RPA & ARŞİV KORUMA DOKTORU ─────────────────────
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: rpaCardCol.implicitHeight + (root.compactHeight ? 24 : 36)
                        radius: 18; color: clrCard; border.color: clrCardBorder; border.width: 1

                        ColumnLayout {
                            id: rpaCardCol
                            anchors.fill: parent
                            anchors.margins: root.responsiveCardPadding
                            spacing: root.responsiveCardSpacing

                            RowLayout {
                                spacing: 12; Layout.fillWidth: true
                                Rectangle {
                                    width: 38; height: root.responsiveButtonHeight; radius: 10; color: Qt.rgba(245, 158, 11, 0.1)
                                    border.color: Qt.rgba(245, 158, 11, 0.3); border.width: 1
                                    Label { anchors.centerIn: parent; text: "📦"; font.pixelSize: 18 }
                                }
                                ColumnLayout {
                                    spacing: 1; Layout.fillWidth: true
                                    Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("tool_unrpa_title", "Arşiv & AST Çözücü"); font.pixelSize: 15; font.bold: true; color: clrTxt }
                                    Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("ln_tool_unrpa_subtitle", "Unrpa & AST decompile engine"); font.pixelSize: 11; color: clrTxtDim }
                                }
                                Rectangle {
                                    radius: 6; color: Qt.rgba(245, 158, 11, 0.15)
                                    Layout.preferredHeight: 20; Layout.preferredWidth: 60
                                    Label { anchors.centerIn: parent; text: appBackend.uiTrigger, appBackend.getTextWithDefault("ln_tool_unrpa_badge", "PIPELINE"); font.pixelSize: 9; font.bold: true; color: clrWarn }
                                }
                            }

                            Label {
                                text: appBackend.uiTrigger, appBackend.getTextWithDefault("tool_unrpa_desc", "Opens .rpa files automatically and recovers text from .rpyc files when needed. This happens automatically in the background during translation.")
                                font.pixelSize: root.compactHeight ? 11 : 12; color: clrTxt2; wrapMode: Text.Wrap; Layout.fillWidth: true
                            }

                            Rectangle {
                                Layout.fillWidth: true; height: root.responsiveButtonHeight; radius: 10
                                color: Qt.rgba(245, 158, 11, 0.08)
                                border.color: Qt.rgba(245, 158, 11, 0.2); border.width: 1
                                Label {
                                    anchors.centerIn: parent
                                    text: appBackend.uiTrigger, "✓ " + appBackend.getTextWithDefault("tool_unrpa_status", "Çeviri başlatıldığında otomatik devreye girer")
                                    color: clrWarn; font.pixelSize: 11; font.bold: true
                                }
                            }
                        }
                    }

                    // ── KART: ACTUALIZACIONES ─────────────────────────────────
                    Rectangle {
                        id: updatesCard
                        objectName: "toolUpdatesCard"
                        Layout.fillWidth: true
                        Layout.preferredHeight: updatesCardCol.implicitHeight + (root.compactHeight ? 24 : 36)
                        radius: 18; color: clrCard; border.color: clrCardBorder; border.width: 1

                        property string statusText: ""
                        property bool checking: false
                        Connections {
                            target: appBackend
                            function onUpdateCheckFinished(hasUpdate, message) {
                                updatesCard.checking = false
                                updatesCard.statusText = message
                            }
                        }

                        ColumnLayout {
                            id: updatesCardCol
                            anchors.fill: parent
                            anchors.margins: root.responsiveCardPadding
                            spacing: root.responsiveCardSpacing

                            RowLayout {
                                spacing: 12; Layout.fillWidth: true
                                Rectangle {
                                    width: 38; height: root.responsiveButtonHeight; radius: 10; color: Qt.rgba(167, 139, 250, 0.1)
                                    border.color: Qt.rgba(167, 139, 250, 0.3); border.width: 1
                                    Label { anchors.centerIn: parent; text: "🔄"; font.pixelSize: 18 }
                                }
                                ColumnLayout {
                                    spacing: 1; Layout.fillWidth: true
                                    Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("tool_updates_title", "Updates"); font.pixelSize: 15; font.bold: true; color: clrTxt }
                                    Label {
                                        text: appBackend.uiTrigger, appBackend.getTextWithDefault("tool_updates_installed", "Installed version: {version}").replace("{version}", "v" + appBackend.version)
                                        font.pixelSize: 11; color: clrTxtDim
                                    }
                                }
                                Rectangle {
                                    radius: 6; color: Qt.rgba(167, 139, 250, 0.15)
                                    Layout.preferredHeight: 20; Layout.preferredWidth: 62
                                    Label { anchors.centerIn: parent; text: appBackend.uiTrigger, appBackend.getTextWithDefault("ln_tool_updates_badge", "UPDATE"); font.pixelSize: 9; font.bold: true; color: clrPurple }
                                }
                            }

                            Label {
                                text: appBackend.uiTrigger, appBackend.getTextWithDefault("tool_updates_desc", "Checks whether a newer LinguaNova has been published. The installed version can download and install it by itself; the portable version opens the download page.")
                                font.pixelSize: root.compactHeight ? 11 : 12; color: clrTxt2; wrapMode: Text.Wrap; Layout.fillWidth: true
                            }

                            CheckBox {
                                id: updatesStartupCheck
                                objectName: "toolUpdatesStartupCheck"
                                Layout.fillWidth: true
                                checked: appBackend.checkForUpdatesOnStartup
                                onToggled: appBackend.checkForUpdatesOnStartup = checked
                                contentItem: Label {
                                    leftPadding: updatesStartupCheck.indicator.width + 8
                                    text: appBackend.uiTrigger, appBackend.getTextWithDefault("tool_updates_startup", "Check for updates when LinguaNova starts")
                                    color: clrTxt2; font.pixelSize: 12; wrapMode: Text.Wrap
                                    verticalAlignment: Text.AlignVCenter
                                }
                            }

                            Button {
                                id: btnCheckUpdates
                                objectName: "toolCheckUpdatesButton"
                                Layout.fillWidth: true; height: root.responsiveButtonHeight
                                enabled: !updatesCard.checking && !appBackend.updateDownloading
                                text: appBackend.uiTrigger, "🔄 " + appBackend.getTextWithDefault("btn_check_updates", "Check for updates")
                                onClicked: {
                                    updatesCard.checking = true
                                    updatesCard.statusText = appBackend.getTextWithDefault("update_checking", "Checking for updates...")
                                    appBackend.checkForUpdates(true)
                                }
                                background: Rectangle {
                                    radius: 10; color: parent.hovered ? clrCardHover : clrInput
                                    border.color: parent.hovered ? clrPurple : clrCardBorder; border.width: 1
                                }
                                contentItem: Label { text: parent.text; color: clrPurple; font.pixelSize: 12; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                            }

                            Label {
                                visible: updatesCard.statusText.length > 0
                                text: updatesCard.statusText
                                font.pixelSize: 11; color: clrTxt2; wrapMode: Text.Wrap; Layout.fillWidth: true
                            }
                        }
                    }

                    // ── KART: IDIOMA DE LA INTERFAZ CREADO POR EL USUARIO ──────
                    Rectangle {
                        id: uiLangCard
                        objectName: "toolUiLanguageCard"
                        Layout.fillWidth: true
                        Layout.preferredHeight: uiLangCardCol.implicitHeight + (root.compactHeight ? 24 : 36)
                        radius: 18; color: clrCard; border.color: clrCardBorder; border.width: 1

                        property bool busy: false
                        property string statusText: ""
                        property var langs: []
                        Component.onCompleted: langs = appBackend.getTargetLanguages()
                        Connections {
                            target: appBackend
                            function onUiLanguageGenerationFinished(ok, message) {
                                uiLangCard.busy = false
                                uiLangCard.statusText = message
                            }
                        }

                        ColumnLayout {
                            id: uiLangCardCol
                            anchors.fill: parent
                            anchors.margins: root.responsiveCardPadding
                            spacing: root.responsiveCardSpacing

                            RowLayout {
                                spacing: 12; Layout.fillWidth: true
                                Rectangle {
                                    width: 38; height: root.responsiveButtonHeight; radius: 10; color: Qt.rgba(56, 189, 248, 0.1)
                                    border.color: Qt.rgba(56, 189, 248, 0.3); border.width: 1
                                    Label { anchors.centerIn: parent; text: "🗣️"; font.pixelSize: 18 }
                                }
                                ColumnLayout {
                                    spacing: 1; Layout.fillWidth: true
                                    Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("tool_ui_lang_title", "Create an interface language"); font.pixelSize: 15; font.bold: true; color: clrTxt }
                                    Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("tool_ui_lang_subtitle", "Machine-translated draft of the interface"); font.pixelSize: 11; color: clrTxtDim }
                                }
                                Rectangle {
                                    radius: 6; color: Qt.rgba(56, 189, 248, 0.15)
                                    Layout.preferredHeight: 20; Layout.preferredWidth: 48
                                    Label { anchors.centerIn: parent; text: appBackend.uiTrigger, appBackend.getTextWithDefault("ln_tool_ui_lang_badge", "UI"); font.pixelSize: 9; font.bold: true; color: "#38BDF8" }
                                }
                            }

                            Label {
                                text: appBackend.uiTrigger, appBackend.getTextWithDefault("tool_ui_lang_desc", "For people who do not speak any of the interface languages: LinguaNova translates its own texts into the chosen language with the selected engine. It is a draft; texts it cannot translate stay in English. You can also edit or add .json files in the languages folder.")
                                font.pixelSize: root.compactHeight ? 11 : 12; color: clrTxt2; wrapMode: Text.Wrap; Layout.fillWidth: true
                            }

                            ComboBox {
                                id: uiLangTargetCombo
                                objectName: "toolUiLanguageCombo"
                                Layout.fillWidth: true; height: root.responsiveButtonHeight
                                model: uiLangCard.langs
                                textRole: "name"; valueRole: "code"
                                enabled: !uiLangCard.busy
                                background: Rectangle { radius: 10; color: clrInput; border.color: parent.hovered ? "#38BDF8" : clrCardBorder; border.width: 1 }
                                contentItem: Label { leftPadding: 14; rightPadding: 30; text: uiLangTargetCombo.displayText; elide: Text.ElideRight; color: clrTxt; font.pixelSize: 12; verticalAlignment: Text.AlignVCenter }
                                delegate: ItemDelegate {
                                    width: uiLangTargetCombo.width
                                    contentItem: Label { text: modelData.name; color: clrTxt; font.pixelSize: 12; leftPadding: 14; elide: Text.ElideRight }
                                    background: Rectangle { color: hovered ? Qt.rgba(56, 189, 248, 0.12) : "transparent" }
                                }
                                popup: Popup {
                                    y: uiLangTargetCombo.height; width: uiLangTargetCombo.width
                                    implicitHeight: Math.min(contentItem.implicitHeight, 260); padding: 4
                                    contentItem: ListView { clip: true; implicitHeight: contentHeight; model: uiLangTargetCombo.delegateModel; ScrollBar.vertical: ScrollBar {} }
                                    background: Rectangle { color: clrCard; radius: 10; border.color: clrCardBorder; border.width: 1 }
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true; spacing: 8
                                Button {
                                    id: btnCreateUiLang
                                    objectName: "toolCreateUiLanguageButton"
                                    Layout.fillWidth: true; height: root.responsiveButtonHeight
                                    enabled: !uiLangCard.busy && uiLangTargetCombo.currentIndex >= 0
                                    text: appBackend.uiTrigger, "🗣️ " + appBackend.getTextWithDefault("btn_create_ui_lang", "Create language")
                                    onClicked: {
                                        uiLangCard.busy = true
                                        uiLangCard.statusText = appBackend.getTextWithDefault("ui_lang_working", "Translating the interface... this can take a few minutes.")
                                        appBackend.createUiLanguage(uiLangTargetCombo.currentValue)
                                    }
                                    background: Rectangle {
                                        radius: 10; color: parent.hovered ? clrCardHover : clrInput
                                        border.color: parent.hovered ? "#38BDF8" : clrCardBorder; border.width: 1
                                    }
                                    contentItem: Label { text: parent.text; color: "#38BDF8"; font.pixelSize: 12; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
                                }
                                Button {
                                    Layout.fillWidth: true; height: root.responsiveButtonHeight
                                    text: appBackend.uiTrigger, "📂 " + appBackend.getTextWithDefault("btn_open_ui_lang_folder", "Languages folder")
                                    onClicked: Qt.openUrlExternally(appBackend.userLocalesFolderUrl())
                                    background: Rectangle {
                                        radius: 10; color: parent.hovered ? clrCardHover : clrInput
                                        border.color: parent.hovered ? clrTxt2 : clrCardBorder; border.width: 1
                                    }
                                    contentItem: Label { text: parent.text; color: clrTxt2; font.pixelSize: 12; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
                                }
                                Button {
                                    Layout.preferredWidth: 38; Layout.preferredHeight: root.responsiveButtonHeight
                                    onClicked: appBackend.reloadUserLanguages()
                                    ToolTip.visible: hovered
                                    ToolTip.delay: 250
                                    ToolTip.text: appBackend.uiTrigger, appBackend.getTextWithDefault("btn_reload_ui_langs", "Reload the languages folder")
                                    background: Rectangle {
                                        radius: 10; color: parent.hovered ? clrCardHover : clrInput
                                        border.color: parent.hovered ? "#38BDF8" : clrCardBorder; border.width: 1
                                    }
                                    contentItem: Label { text: "⟳"; color: clrTxt2; font.pixelSize: 17; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                }
                            }

                            Label {
                                visible: uiLangCard.statusText.length > 0
                                text: uiLangCard.statusText
                                font.pixelSize: 11; color: clrTxt2; wrapMode: Text.Wrap; Layout.fillWidth: true
                            }
                        }
                    }
                }

                Item { height: root.compactHeight ? 12 : 24 }
            }
        }

        // ═════════════════════════════════════════════════════════════
        // SEKME 4: GLOSSARY — TERİM SÖZLÜĞÜ YÖNETİMİ
        // ═════════════════════════════════════════════════════════════
        // ═════════════════════════════════════════════════════════════
        // SEKME 4: GLOSSARY — TERİM SÖZLÜĞÜ YÖNETİMİ
        // ═════════════════════════════════════════════════════════════
        Item {
            id: pageGlossary
            visible: navIndex === 4
            Layout.fillWidth: true
            Layout.fillHeight: true

            property string searchQuery: ""

            transform: Translate { id: animTrGlossary; y: 14 }
            opacity: 0.0
            ParallelAnimation {
                id: animEntranceGlossary
                NumberAnimation { target: animTrGlossary; property: "y"; from: 14; to: 0; duration: 220; easing.type: Easing.OutCubic }
                NumberAnimation { target: pageGlossary; property: "opacity"; from: 0.0; to: 1.0; duration: 180; easing.type: Easing.OutQuad }
            }
            onVisibleChanged: if (visible) animEntranceGlossary.restart()

            // Sabit Sticky Header (Arama + İşlem Araç Çubuğu)
            Rectangle {
                id: glossaryStickyHeader
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                height: 114
                z: 10
                color: clrBg
                border.color: clrCardBorder
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 10

                    // Üst Satır: Başlık & Rozet & Sayaç & Aksiyonlar
                    RowLayout {
                        Layout.fillWidth: true; spacing: 12
                        Rectangle {
                            width: 36; height: 36; radius: 10
                            color: Qt.rgba(16, 185, 129, 0.12)
                            border.color: Qt.rgba(16, 185, 129, 0.3); border.width: 1
                            Label { anchors.centerIn: parent; text: "📚"; font.pixelSize: 18 }
                        }
                        ColumnLayout {
                            spacing: 1
                            Label {
                                text: appBackend.uiTrigger, appBackend.getTextWithDefault("ln_glossary_title", "Diccionario de consistencia")
                                font.pixelSize: 17; font.bold: true; color: clrTxt
                            }
                            Label {
                                text: appBackend.uiTrigger, (pageGlossary.filteredGlossaryModel().length) + " / " + (appBackend.glossaryList ? appBackend.glossaryList.length : 0) + " " + appBackend.getTextWithDefault("glossary_count", "terms loaded.")
                                font.pixelSize: 11; color: clrTxt2
                            }
                        }
                        Item { Layout.fillWidth: true }

                        // Eylemler
                        Button {
                            height: 34; text: appBackend.uiTrigger, "➕ " + appBackend.getTextWithDefault("glossary_btn_add", "Add Term")
                            onClicked: { addGlossarySource.text = ""; addGlossaryTarget.text = ""; addGlossaryDialog.open() }
                            background: Rectangle { radius: 10; color: parent.hovered ? clrCardHover : clrInput; border.color: clrAccent; border.width: 1 }
                            contentItem: Label { text: parent.text; color: clrAccent; font.pixelSize: 11; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                        }
                        Button {
                            height: 34; text: appBackend.uiTrigger, "📥 " + appBackend.getTextWithDefault("glossary_btn_import", "Import")
                            onClicked: importGlossaryDialog.open()
                            background: Rectangle { radius: 10; color: parent.hovered ? clrCardHover : clrInput; border.color: clrCardBorder; border.width: 1 }
                            contentItem: Label { text: parent.text; color: clrTxt; font.pixelSize: 11; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                        }
                        Button {
                            height: 34; text: appBackend.uiTrigger, "📤 " + appBackend.getTextWithDefault("glossary_btn_export", "Export")
                            onClicked: exportGlossaryDialog.open()
                            background: Rectangle { radius: 10; color: parent.hovered ? clrCardHover : clrInput; border.color: clrCardBorder; border.width: 1 }
                            contentItem: Label { text: parent.text; color: clrTxt; font.pixelSize: 11; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                        }
                        Button {
                            height: 34; text: appBackend.uiTrigger, "📋 " + appBackend.getTextWithDefault("glossary_btn_fill", "Fill Source")
                            onClicked: appBackend.fillEmptyGlossaryWithSource()
                            background: Rectangle { radius: 10; color: parent.hovered ? clrCardHover : clrInput; border.color: clrCardBorder; border.width: 1 }
                            contentItem: Label { text: parent.text; color: clrTxt; font.pixelSize: 11; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                        }
                        Button {
                            height: 34; text: appBackend.uiTrigger, "🌐 " + appBackend.getTextWithDefault("glossary_btn_translate", "Translate Empty")
                            onClicked: appBackend.translateEmptyGlossary()
                            background: Rectangle { radius: 10; color: parent.hovered ? clrCardHover : clrInput; border.color: clrPurple; border.width: 1 }
                            contentItem: Label { text: parent.text; color: clrPurple; font.pixelSize: 11; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                        }
                    }

                    // Alt Satır: Arama Çubuğu
                    RowLayout {
                        Layout.fillWidth: true; spacing: 10
                        Rectangle {
                            Layout.fillWidth: true; height: 32; radius: 10; color: clrInput; border.color: clrCardBorder; border.width: 1
                            RowLayout {
                                anchors.fill: parent; anchors.leftMargin: 10; anchors.rightMargin: 10; spacing: 8
                                Label { text: "🔍"; font.pixelSize: 12; color: clrTxtDim }
                                TextInput {
                                    id: glossarySearchInput
                                    Layout.fillWidth: true
                                    font.pixelSize: 12; color: clrTxt
                                    clip: true
                                    Text {
                                        anchors.fill: parent
                                        verticalAlignment: Text.AlignVCenter
                                        text: appBackend.uiTrigger, appBackend.getTextWithDefault("glossary_search_placeholder", "Sözlükte terim veya çeviri ara...")
                                        color: clrTxtDim; font.pixelSize: 12
                                        visible: !glossarySearchInput.text && !glossarySearchInput.activeFocus
                                    }
                                    onTextChanged: pageGlossary.searchQuery = text.trim().toLowerCase()
                                }
                                Button {
                                    visible: glossarySearchInput.text.length > 0
                                    width: 18; height: 18
                                    text: "✕"
                                    onClicked: { glossarySearchInput.text = ""; pageGlossary.searchQuery = "" }
                                    background: Item {}
                                    contentItem: Label { text: "✕"; color: clrTxtDim; font.pixelSize: 10; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                }
                            }
                        }
                    }
                }
            }

            function filteredGlossaryModel() {
                appBackend.uiTrigger
                var list = appBackend.glossaryList || []
                var q = pageGlossary.searchQuery
                if (!q) return list
                var result = []
                for (var i = 0; i < list.length; i++) {
                    var item = list[i]
                    var s = (item.source || "").toLowerCase()
                    var t = (item.target || "").toLowerCase()
                    if (s.indexOf(q) !== -1 || t.indexOf(q) !== -1) {
                        result.push(item)
                    }
                }
                return result
            }

            // Scroll Edilebilir İçerik (Liste & Empty State)
            ScrollView {
                id: viewGlossary
                anchors.top: glossaryStickyHeader.bottom
                anchors.bottom: parent.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                clip: true
                contentWidth: availableWidth
                contentHeight: glossaryContent.implicitHeight + (root.responsivePageMargin * 2)
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                ScrollBar.vertical.policy: root.needsPageScroll(viewGlossary.contentHeight, viewGlossary.availableHeight)
                                               ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff

                ColumnLayout {
                    id: glossaryContent
                    y: root.responsivePageMargin
                    width: Math.max(0, Math.min(viewGlossary.availableWidth - (root.responsivePageMargin * 2), 1180))
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: root.compactHeight ? 8 : 10

                    // Tablo Başlığı
                    RowLayout {
                        Layout.fillWidth: true; spacing: 12
                        Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("glossary_col_source", "Source (Original)"); font.pixelSize: 12; font.bold: true; color: clrTxt2; Layout.fillWidth: true; Layout.preferredWidth: 320 }
                        Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("glossary_col_target", "Target (Translation)"); font.pixelSize: 12; font.bold: true; color: clrTxt2; Layout.fillWidth: true }
                        Item { Layout.preferredWidth: 40 }
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: clrCardBorder }

                    // Boş Durum (Empty State) Kartı
                    Rectangle {
                        visible: pageGlossary.filteredGlossaryModel().length === 0
                        Layout.fillWidth: true; Layout.preferredHeight: 180
                        radius: 18; color: clrCard; border.color: clrCardBorder; border.width: 1
                        ColumnLayout {
                            anchors.centerIn: parent; spacing: 10
                            Label { text: "📖"; font.pixelSize: 36; Layout.alignment: Qt.AlignHCenter }
                            Label {
                                text: appBackend.uiTrigger, pageGlossary.searchQuery.length > 0
                                    ? appBackend.getTextWithDefault("glossary_no_search_results", "Aramanızla eşleşen terim bulunamadı.")
                                    : appBackend.getTextWithDefault("glossary_empty_state", "Henüz terim eklenmedi. '➕ Terim Ekle' veya '📥 İçe Aktar' ile başlayın.")
                                font.pixelSize: 13; color: clrTxt2; font.bold: true; Layout.alignment: Qt.AlignHCenter
                            }
                        }
                    }

                    // Terimler Listesi (ListView)
                    ListView {
                        id: glossaryListView
                        Layout.fillWidth: true
                        Layout.preferredHeight: contentHeight
                        model: pageGlossary.filteredGlossaryModel()
                        clip: true; interactive: false
                        spacing: 8
                        delegate: RowLayout {
                            width: glossaryListView.width; spacing: 12
                            Rectangle {
                                Layout.fillWidth: true; Layout.preferredWidth: 320; height: 42; radius: 10
                                color: clrInput; border.color: clrCardBorder; border.width: 1
                                Label {
                                    anchors.fill: parent; anchors.margins: 12
                                    text: modelData.source; color: clrTxt; font.pixelSize: 12
                                    elide: Text.ElideRight; verticalAlignment: Text.AlignVCenter
                                }
                            }
                            Rectangle {
                                Layout.fillWidth: true; height: 42; radius: 10
                                color: clrInput; border.color: modelData.target ? clrCardBorder : Qt.rgba(239, 68, 68, 0.35); border.width: 1
                                Label {
                                    anchors.fill: parent; anchors.margins: 12
                                    text: modelData.target || appBackend.getTextWithDefault("glossary_empty", "(empty)"); color: modelData.target ? clrTxt : clrError
                                    font.pixelSize: 12; elide: Text.ElideRight; verticalAlignment: Text.AlignVCenter
                                }
                            }
                            Button {
                                Layout.preferredWidth: 36; height: 36
                                text: "✕"
                                onClicked: appBackend.removeGlossaryItem(modelData.source)
                                background: Rectangle { radius: 10; color: parent.hovered ? "#3B1111" : "transparent"; border.color: "transparent" }
                                contentItem: Label { text: "✕"; color: clrError; font.pixelSize: 14; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                            }
                        }
                    }

                    Item { height: 24 }
                }
            }
        }

        // ═════════════════════════════════════════════════════════════
        // SEKME 5: ÇEVİRİ EDİTÖRÜ (tl/<dil> satır satır düzenleme)
        // ═════════════════════════════════════════════════════════════
        EditorPage {
            id: pageEditor
            ui: root
            visible: navIndex === 5
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
        // ═════════════════════════════════════════════════════════════
        // #MOD — PÁGINA 6: MOD DE INTERFAZ
        // Completamente separado del sistema normal de traducción.
        // Las nuevas peticiones se añaden a la cola FIFO y NUNCA cancelan
        // el trabajo activo.
        // ═════════════════════════════════════════════════════════════
        Item {
            id: pageMod
            visible: navIndex === 6
            Layout.fillWidth: true
            Layout.fillHeight: true

            ScrollView {
                id: viewMod
                anchors.fill: parent
                clip: true
                contentWidth: availableWidth
                contentHeight: modContent.implicitHeight + ((root.compactHeight ? 10 : root.responsivePageMargin) * 2)
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                ScrollBar.vertical.policy: root.needsPageScroll(viewMod.contentHeight, viewMod.availableHeight)
                                               ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff

                ColumnLayout {
                    id: modContent
                    y: root.compactHeight ? 10 : root.responsivePageMargin
                    width: Math.max(
                               0,
                               Math.min(
                                   viewMod.availableWidth - ((root.compactHeight ? 12 : root.responsivePageMargin) * 2),
                                   1320
                               )
                           )
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: root.compactHeight ? 10 : root.responsiveSectionSpacing

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12
                        Label { text: "🧩"; font.pixelSize: root.compactHeight ? 24 : 30; verticalAlignment: Text.AlignVCenter }
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Label {
                                text: appBackend.uiTrigger, appBackend.getTextWithDefault("mod_title", "MOD")
                                color: clrTxt; font.bold: true; font.pixelSize: root.compactHeight ? 22 : 26
                            }
                            Label {
                                Layout.fillWidth: true
                                text: appBackend.uiTrigger, appBackend.getTextWithDefault(
                                          "mod_subtitle",
                                          "Generate a standalone translation MOD for Ren'Py game interfaces.")
                                color: clrTxt2; font.pixelSize: root.compactHeight ? 11 : 12; wrapMode: Text.WordWrap
                            }
                        }
                        Rectangle {
                            Layout.preferredWidth: queueLbl.implicitWidth + 24
                            Layout.preferredHeight: root.compactHeight ? 26 : 30
                            radius: root.compactHeight ? 13 : 15
                            color: clrInput
                            border.color: clrCardBorder
                            Label {
                                id: queueLbl
                                anchors.centerIn: parent
                                text: appBackend.uiTrigger, appBackend.getTextWithDefault("mod_queue", "Queue") + ": " + appBackend.workQueueCount
                                color: appBackend.workQueueCount > 0 ? clrWarn : clrTxt2
                                font.pixelSize: 10; font.bold: true
                            }
                        }
                    }

                    // #MOD — En pantallas bajas como 1366x768, estas tres tarjetas
                    // comparten una fila cuando existe ancho suficiente. En ventanas
                    // estrechas vuelven automáticamente a una sola columna.
                    GridLayout {
                        id: modInfoGrid
                        Layout.fillWidth: true
                        columns: root.compactHeight && !root.compactWidth ? 3 : 1
                        columnSpacing: root.compactHeight ? 10 : root.responsiveSectionSpacing
                        rowSpacing: root.compactHeight ? 10 : root.responsiveSectionSpacing

                        Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: root.compactHeight && !root.compactWidth
                        Layout.preferredHeight: modInfoCol.implicitHeight + (root.compactHeight ? 22 : 40)
                        radius: 16; color: clrCard; border.color: clrCardBorder; border.width: 1
                        ColumnLayout {
                            id: modInfoCol
                            anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                            anchors.margins: root.compactHeight ? 11 : 20; spacing: root.compactHeight ? 6 : 10
                            Label {
                                Layout.fillWidth: true
                                text: appBackend.uiTrigger, appBackend.getTextWithDefault("mod_isolation_title", "🛡 Isolated from the main translator")
                                color: clrAccent; font.bold: true; font.pixelSize: root.compactHeight ? 12 : 14; wrapMode: Text.WordWrap
                            }
                            Label {
                                Layout.fillWidth: true
                                text: appBackend.uiTrigger, appBackend.getTextWithDefault(
                                          "mod_isolation_desc",
                                          "MOD uses its own independent analyzer. It reads visible .rpy files first and only uses compiled or packaged game files when something is missing. It never changes the original game scripts or the normal LinguaNova translation system.")
                                color: clrTxt2; font.pixelSize: root.compactHeight ? 10 : 11; lineHeight: root.compactHeight ? 1.1 : 1.2; wrapMode: Text.WordWrap
                            }
                        }
                    }

                        Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: root.compactHeight && !root.compactWidth
                        Layout.preferredHeight: modInGameInfoCol.implicitHeight + (root.compactHeight ? 22 : 40)
                        radius: 16; color: clrCard; border.color: clrCardBorder; border.width: 1
                        ColumnLayout {
                            id: modInGameInfoCol
                            anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                            anchors.margins: root.compactHeight ? 11 : 20; spacing: root.compactHeight ? 6 : 10
                            Label {
                                Layout.fillWidth: true
                                text: appBackend.uiTrigger, appBackend.getTextWithDefault("mod_ingame_title", "🎮 How the MOD appears in the game")
                                color: clrAccent; font.bold: true; font.pixelSize: root.compactHeight ? 12 : 14; wrapMode: Text.WordWrap
                            }
                            Label {
                                Layout.fillWidth: true
                                text: appBackend.uiTrigger, appBackend.getTextWithDefault(
                                          "mod_ingame_desc",
                                          "The MOD does not add extra buttons and does not require a special key. Ren'Py loads the generated linguanova_mod_<game>_<lang>.rpy automatically when the game starts. The existing screens, layout, buttons, styles and actions remain unchanged; only the detected interface text is replaced.")
                                color: clrTxt2; font.pixelSize: root.compactHeight ? 10 : 11; lineHeight: root.compactHeight ? 1.1 : 1.2; wrapMode: Text.WordWrap
                            }
                            Label {
                                Layout.fillWidth: true
                                text: appBackend.uiTrigger, appBackend.getTextWithDefault(
                                          "mod_ingame_independent",
                                          "It can be used independently of LinguaNova's full translation and can coexist with a translation obtained elsewhere.")
                                color: clrTxt2; font.pixelSize: root.compactHeight ? 10 : 11; lineHeight: root.compactHeight ? 1.1 : 1.2; wrapMode: Text.WordWrap
                            }
                        }
                    }

                        Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: root.compactHeight && !root.compactWidth
                        Layout.preferredHeight: modHookInfoCol.implicitHeight + (root.compactHeight ? 22 : 40)
                        radius: 16; color: clrCard; border.color: clrCardBorder; border.width: 1
                        ColumnLayout {
                            id: modHookInfoCol
                            anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                            anchors.margins: root.compactHeight ? 11 : 20; spacing: root.compactHeight ? 6 : 10
                            Label {
                                Layout.fillWidth: true
                                text: appBackend.uiTrigger, appBackend.getTextWithDefault("mod_hook_compare_title", "🧩 Normal translation and MOD: how they stay separate")
                                color: clrAccent2; font.bold: true; font.pixelSize: root.compactHeight ? 12 : 14; wrapMode: Text.WordWrap
                            }
                            Label {
                                Layout.fillWidth: true
                                text: appBackend.uiTrigger, appBackend.getTextWithDefault(
                                          "mod_hook_main_desc",
                                          "Normal translation: works with the complete game translation and includes the extra mechanisms needed to recover text that changes while the game is running.")
                                color: clrTxt2; font.pixelSize: root.compactHeight ? 10 : 11; lineHeight: root.compactHeight ? 1.1 : 1.2; wrapMode: Text.WordWrap
                            }
                            Label {
                                Layout.fillWidth: true
                                text: appBackend.uiTrigger, appBackend.getTextWithDefault(
                                          "mod_hook_mod_desc",
                                          "MOD: uses a separate system created only for interface text. It applies translations only where those interface texts were detected and never changes the normal LinguaNova translation system.")
                                color: clrTxt2; font.pixelSize: root.compactHeight ? 10 : 11; lineHeight: root.compactHeight ? 1.1 : 1.2; wrapMode: Text.WordWrap
                            }
                        }
                    }

                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: modActionsCol.implicitHeight + (root.compactHeight ? 24 : 40)
                        radius: 16; color: clrCard; border.color: clrCardBorder; border.width: 1
                        ColumnLayout {
                            id: modActionsCol
                            anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                            anchors.margins: root.compactHeight ? 12 : 20
                            spacing: root.compactHeight ? 9 : 14

                            Label {
                                Layout.fillWidth: true
                                text: appBackend.uiTrigger, appBackend.getTextWithDefault("mod_actions_title", "Interface MOD")
                                color: clrTxt; font.bold: true; font.pixelSize: 15
                            }
                            Label {
                                Layout.fillWidth: true
                                text: appBackend.uiTrigger, appBackend.getTextWithDefault(
                                          "mod_actions_desc",
                                          "Choose the game directly from this MOD page. LinguaNova inspects its interface text and uses the currently selected source language, target language and translation service. Story and dialogue are not translated by this MOD.")
                                color: clrTxt2; font.pixelSize: 11; wrapMode: Text.WordWrap; lineHeight: 1.2
                            }

                            Label {
                                Layout.fillWidth: true
                                text: appBackend.uiTrigger, appBackend.getTextWithDefault(
                                          "mod_game_path_title", "Selected game")
                                color: clrTxt; font.bold: true; font.pixelSize: 12
                            }

                            TextField {
                                id: modProjectPathField
                                Layout.fillWidth: true
                                readOnly: true
                                selectByMouse: true
                                text: appBackend.modProjectPath
                                placeholderText: appBackend.uiTrigger, appBackend.getTextWithDefault(
                                                     "mod_game_path_empty",
                                                     "No game has been selected for MOD yet.")
                                color: clrTxt
                                placeholderTextColor: clrTxtDim
                                background: Rectangle {
                                    radius: 10
                                    color: clrInput
                                    border.color: clrCardBorder
                                    border.width: 1
                                }
                            }

                            Label {
                                Layout.fillWidth: true
                                text: appBackend.uiTrigger, appBackend.getTextWithDefault(
                                          "mod_scan_scope_desc",
                                          "You can select the game executable, the main game folder, or the game folder itself. LinguaNova then finds the game folder automatically and inspects the complete game folder, including visible scripts and packaged/compiled scripts when needed. Translation folders, saves and temporary game data are skipped.")
                                color: clrTxt2
                                font.pixelSize: 10
                                lineHeight: 1.2
                                wrapMode: Text.WordWrap
                            }

                            GridLayout {
                                Layout.fillWidth: true
                                columns: root.narrowWidth ? 1 : 3
                                columnSpacing: 10
                                rowSpacing: root.compactHeight ? 6 : 10
                                Button {
                                    Layout.preferredWidth: root.compactWidth ? 190 : 220
                                    Layout.preferredHeight: root.responsiveButtonHeight
                                    text: appBackend.uiTrigger, appBackend.getTextWithDefault(
                                              "mod_select_analyze_btn", "Select game and inspect")
                                    onClicked: {
                                        if (Qt.platform.os === "windows")
                                            modGameFileDialog.open()
                                        else
                                            modGameFolderDialog.open()
                                    }
                                }
                                Button {
                                    Layout.preferredWidth: root.compactWidth ? 130 : 150
                                    Layout.preferredHeight: root.responsiveButtonHeight
                                    text: appBackend.uiTrigger, appBackend.getTextWithDefault(
                                              "mod_select_folder_btn", "Choose folder")
                                    onClicked: modGameFolderDialog.open()
                                }
                                Button {
                                    Layout.preferredWidth: root.compactWidth ? 165 : 190
                                    Layout.preferredHeight: root.responsiveButtonHeight
                                    enabled: appBackend.modProjectPath.length > 0
                                    text: appBackend.uiTrigger, appBackend.getTextWithDefault("mod_generate_btn", "Generate MOD")
                                    onClicked: appBackend.generateMod()
                                }
                                BusyIndicator {
                                    running: appBackend.modRunning
                                    visible: running
                                    Layout.preferredWidth: 28
                                    Layout.preferredHeight: 28
                                }
                                Item { Layout.fillWidth: true }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: modStatusLbl.implicitHeight + 24
                                radius: 12; color: clrInput; border.color: clrCardBorder
                                Label {
                                    id: modStatusLbl
                                    anchors.fill: parent; anchors.margins: 12
                                    text: appBackend.modStatus
                                    color: appBackend.modRunning || appBackend.modPartial ? clrWarn : clrTxt2
                                    font.pixelSize: 11; wrapMode: Text.WordWrap
                                }
                            }

                            GridLayout {
                                Layout.fillWidth: true
                                columns: root.narrowWidth ? 2 : 3
                                columnSpacing: 12; rowSpacing: 8
                                Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("mod_stats_detected", "Detected") + ": " + appBackend.modCandidateCount; color: clrTxt2; font.pixelSize: 11 }
                                Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("mod_stats_translated", "Translated") + ": " + appBackend.modTranslatedCount; color: clrSuccess; font.pixelSize: 11 }
                                Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("mod_stats_unchanged", "No change needed") + ": " + appBackend.modUnchangedCount; color: clrTxt2; font.pixelSize: 11 }
                                Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("mod_stats_pending", "Pending") + ": " + appBackend.modRejectedCount; color: appBackend.modRejectedCount > 0 ? clrWarn : clrTxt2; font.pixelSize: 11 }
                                Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("mod_stats_excluded", "Code excluded (not counted)") + ": " + appBackend.modExcludedCount; color: clrTxtDim; font.pixelSize: 11 }
                                Label { text: appBackend.uiTrigger, appBackend.getTextWithDefault("mod_stats_coverage", "Coverage") + ": " + appBackend.modCoverage.toFixed(1) + "%"; color: clrAccent; font.pixelSize: 11 }
                            }

                            Label {
                                Layout.fillWidth: true
                                visible: appBackend.modOutputPath.length > 0
                                text: appBackend.uiTrigger, appBackend.getTextWithDefault("mod_output_label", "Output") + ": " + appBackend.modOutputPath
                                color: clrTxt2; font.pixelSize: 10; wrapMode: Text.WrapAnywhere
                            }
                        }
                    }

                    Item {
                        Layout.fillWidth: true
                        Layout.preferredHeight: root.compactHeight ? 4 : 12
                    }
                }
            }
        }
        }
    }

    // ── Toast Bildirim Köşesi (Fluent Glass & Slide-in) ────────────────────
    ToastNotification {
        id: toast
        parent: root.contentItem
        clrSuccess: root.clrSuccess
        clrError: root.clrError
        clrWarn: root.clrWarn
        clrAccent: root.clrAccent
        clrTxt: root.clrTxt
    }

    // ── Uyarı ve Tamamlanma Popup Diyalogları ─────────────────────────────
    AboutDialog {
        id: aboutDialog
        clrCard: root.clrCard
        clrAccent: root.clrAccent
        clrAccent2: root.clrAccent2
        clrTxt: root.clrTxt
        clrTxt2: root.clrTxt2
        clrInput: root.clrInput
        clrBorder: root.clrCardBorder
    }

    WarningDialog {
        id: warningDialog
        clrCard: root.clrCard
        clrWarn: root.clrWarn
        clrWarnDim: root.clrWarnDim
        clrTxt: root.clrTxt
        clrTxtDim: root.clrTxtDim
        clrInput: root.clrInput
    }

    Dialog {
        id: completionDialog
        anchors.centerIn: parent
        width: Math.min(540, root.width * 0.88)
        padding: 0
        header: null
        footer: null
        modal: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        standardButtons: Dialog.NoButton

        property string summaryText: ""
        property string outputPath: ""
        property string diagPath: ""

        enter: Transition {
            NumberAnimation { property: "opacity"; from: 0.0; to: 1.0; duration: 200; easing.type: Easing.OutCubic }
            NumberAnimation { property: "scale"; from: 0.92; to: 1.0; duration: 240; easing.type: Easing.OutBack; easing.overshoot: 1.3 }
        }
        exit: Transition {
            NumberAnimation { property: "opacity"; from: 1.0; to: 0.0; duration: 150; easing.type: Easing.InQuad }
            NumberAnimation { property: "scale"; from: 1.0; to: 0.94; duration: 150; easing.type: Easing.InQuad }
        }

        Overlay.modal: Rectangle {
            color: Qt.rgba(0, 0, 0, 0.65)
        }

        background: Rectangle {
            color: clrCard
            radius: 18
            border.color: Qt.rgba(184, 243, 107, 0.45)
            border.width: 1.5
            clip: true

            // Üst kısımdaki hafif neon gradyan vurgusu
            Rectangle {
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                height: 3
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0.0; color: clrAccent }
                    GradientStop { position: 1.0; color: clrAccent2 }
                }
            }
        }

        contentItem: ColumnLayout {
            spacing: 18

            // 1. Üst Başlık ve Rozet
            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 22
                Layout.rightMargin: 20
                Layout.topMargin: 20
                spacing: 14

                Rectangle {
                    width: 42; height: 42; radius: 21
                    color: clrSuccessDim
                    border.color: clrSuccess; border.width: 1.5

                    Label {
                        anchors.centerIn: parent
                        text: "🎉"
                        font.pixelSize: 22
                    }
                }

                ColumnLayout {
                    spacing: 3
                    Layout.fillWidth: true

                    Label {
                        text: appBackend.uiTrigger, cleanModalTitle(appBackend.getTextWithDefault("completion_summary_title", "Çeviri ve Derleme Tamamlandı"))
                        font.pixelSize: 17; font.bold: true; color: clrTxt
                    }
                    Label {
                        text: appBackend.uiTrigger, appBackend.getTextWithDefault("completion_summary_subtitle", "Oyun yerelleştirme dosyaları başarıyla üretildi.")
                        font.pixelSize: 12; color: clrTxt2
                    }
                }

                // Sağ üst kapatma '✕' butonu
                Rectangle {
                    width: 32; height: 32; radius: 16
                    color: closeCompletionMa.containsMouse ? Qt.rgba(255, 255, 255, 0.12) : "transparent"
                    scale: closeCompletionMa.pressed ? 0.92 : (closeCompletionMa.containsMouse ? 1.08 : 1.0)
                    Behavior on scale { NumberAnimation { duration: 120 } }
                    Behavior on color { ColorAnimation { duration: 120 } }

                    Label {
                        anchors.centerIn: parent
                        text: "✕"
                        color: closeCompletionMa.containsMouse ? "#FFFFFF" : clrTxtDim
                        font.pixelSize: 13
                        font.bold: true
                    }
                    MouseArea {
                        id: closeCompletionMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: completionDialog.close()
                    }
                }
            }

            // 2. Özet Bilgi Kartı
            Rectangle {
                Layout.fillWidth: true
                Layout.leftMargin: 22
                Layout.rightMargin: 22
                Layout.preferredHeight: summaryCol.implicitHeight + 24
                radius: 14
                color: clrInput
                border.color: Qt.rgba(255, 255, 255, 0.08)
                border.width: 1

                ColumnLayout {
                    id: summaryCol
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 10

                    RowLayout {
                        spacing: 10
                        Layout.fillWidth: true

                        Rectangle {
                            width: 26; height: 26; radius: 6
                            color: Qt.rgba(184, 243, 107, 0.12)
                            Layout.alignment: Qt.AlignTop
                            Label {
                                anchors.centerIn: parent
                                text: "📊"
                                font.pixelSize: 13
                            }
                        }

                        Label {
                            text: completionDialog.summaryText
                            color: clrTxt
                            font.pixelSize: 13
                            font.weight: Font.Medium
                            wrapMode: Text.Wrap
                            Layout.fillWidth: true
                            lineHeight: 1.35
                        }
                    }

                    // Çıktı klasör yolu (varsa)
                    Rectangle {
                        Layout.fillWidth: true
                        height: 32
                        radius: 7
                        color: "#0F0D0B"
                        border.color: Qt.rgba(255, 255, 255, 0.06)
                        border.width: 1
                        visible: completionDialog.outputPath.length > 0

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 10
                            anchors.rightMargin: 10
                            spacing: 8

                            Label {
                                text: "📁"
                                font.pixelSize: 13
                            }
                            Label {
                                text: completionDialog.outputPath
                                color: clrTxtDim
                                font.pixelSize: 11
                                font.family: "Consolas"
                                elide: Text.ElideMiddle
                                Layout.fillWidth: true
                            }
                        }
                    }
                }
            }
            // 3. Alt Butonlar Grubu
            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 22
                Layout.rightMargin: 22
                Layout.bottomMargin: 20
                spacing: 12

                // Çıktı Klasörünü Aç (Secondary Action Button)
                Button {
                    id: openFolderBtn
                    Layout.fillWidth: true; height: 42
                    visible: completionDialog.outputPath.length > 0
                    scale: down ? 0.97 : (hovered ? 1.02 : 1.0)
                    transformOrigin: Item.Center
                    Behavior on scale { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
                    onClicked: if (completionDialog.outputPath) appBackend.openLocalPath(completionDialog.outputPath)

                    background: Rectangle {
                        radius: 12
                        color: openFolderBtn.down ? Qt.rgba(184, 243, 107, 0.18) : (openFolderBtn.hovered ? Qt.rgba(184, 243, 107, 0.10) : clrInput)
                        border.color: openFolderBtn.hovered ? clrAccent : Qt.rgba(255, 255, 255, 0.12)
                        border.width: 1
                        Behavior on color { ColorAnimation { duration: 140 } }
                        Behavior on border.color { ColorAnimation { duration: 140 } }
                    }
                    contentItem: RowLayout {
                        spacing: 8
                        Item { Layout.fillWidth: true }
                        Label { text: "📂"; font.pixelSize: 14 }
                        Label {
                            text: appBackend.uiTrigger, appBackend.getTextWithDefault("open_output_folder", "Çıktı Klasörünü Aç")
                            color: openFolderBtn.hovered ? clrAccent : clrTxt
                            font.bold: true; font.pixelSize: 13
                        }
                        Item { Layout.fillWidth: true }
                    }
                }

                // Tamam (Primary Action Button)
                Button {
                    id: completionOkBtn
                    Layout.preferredWidth: completionDialog.outputPath.length > 0 ? 130 : parent.width
                    Layout.fillWidth: completionDialog.outputPath.length === 0
                    height: 42
                    scale: down ? 0.97 : (hovered ? 1.02 : 1.0)
                    transformOrigin: Item.Center
                    Behavior on scale { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
                    onClicked: completionDialog.close()

                    background: Rectangle {
                        radius: 12
                        color: completionOkBtn.hovered ? "#D8FFA8" : "#B8F36B"
                        gradient: Gradient {
                            orientation: Gradient.Horizontal
                            GradientStop { position: 0.0; color: completionOkBtn.hovered ? "#D8FFA8" : "#B8F36B" }
                            GradientStop { position: 1.0; color: completionOkBtn.hovered ? "#B8F36B" : "#A78BFA" }
                        }
                        Behavior on color { ColorAnimation { duration: 140 } }
                    }
                    contentItem: Label {
                        text: appBackend.uiTrigger, appBackend.getTextWithDefault("dialog_ok", "Tamam")
                        color: "#0F0D0B"
                        font.bold: true
                        font.pixelSize: 13
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }
        }
    }

    Dialog {
        id: updateDialog
        anchors.centerIn: parent
        width: Math.min(480, root.width * 0.85)
        padding: 0
        header: null
        footer: null
        modal: true
        // Not closed by a click outside: it was easy to dismiss by accident.
        closePolicy: Popup.CloseOnEscape
        standardButtons: Dialog.NoButton
        property string latestVersion: ""
        property string currentVersion: ""
        property string releaseUrl: ""
        // Automatic update (installed Windows build): download + verify + install.
        property int progress: 0
        property string statusText: ""
        property bool autoFailed: false
        readonly property bool autoMode: appBackend.canAutoUpdate && !autoFailed
        onOpened: { progress = 0; statusText = ""; autoFailed = false }
        // Tags are usually "v1.0.1"; the label adds its own "v".
        function plainVersion(v) { return (v || "").replace(/^[vV]/, "") }

        enter: Transition {
            NumberAnimation { property: "opacity"; from: 0.0; to: 1.0; duration: 180; easing.type: Easing.OutCubic }
            NumberAnimation { property: "scale"; from: 0.94; to: 1.0; duration: 180; easing.type: Easing.OutCubic }
        }
        exit: Transition {
            NumberAnimation { property: "opacity"; from: 1.0; to: 0.0; duration: 140; easing.type: Easing.InQuad }
            NumberAnimation { property: "scale"; from: 1.0; to: 0.96; duration: 140; easing.type: Easing.InQuad }
        }

        Overlay.modal: Rectangle {
            color: Qt.rgba(0, 0, 0, 0.65)
        }

        background: Rectangle {
            color: clrCard
            radius: 18
            border.color: Qt.rgba(184, 243, 107, 0.45)
            border.width: 1.5
            clip: true

            Rectangle {
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                height: 3
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0.0; color: clrAccent }
                    GradientStop { position: 1.0; color: clrAccent2 }
                }
            }
        }

        contentItem: ColumnLayout {
            spacing: 16

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 20
                Layout.rightMargin: 18
                Layout.topMargin: 20
                spacing: 14

                Rectangle {
                    width: 40; height: 40; radius: 20
                    color: Qt.rgba(184, 243, 107, 0.15)
                    border.color: clrAccent; border.width: 1.5

                    Label {
                        anchors.centerIn: parent
                        text: "🚀"
                        font.pixelSize: 20
                    }
                }

                ColumnLayout {
                    spacing: 2
                    Layout.fillWidth: true

                    Label {
                        text: appBackend.uiTrigger, cleanModalTitle(appBackend.getTextWithDefault("update_available_title", "Yeni Sürüm Mevcut"))
                        font.pixelSize: 17; font.bold: true; color: clrTxt
                    }
                    Label {
                        text: updateDialog.latestVersion.length > 0 ? ("v" + updateDialog.plainVersion(updateDialog.latestVersion)) : ""
                        font.pixelSize: 12; color: clrAccent; font.bold: true
                        visible: updateDialog.latestVersion.length > 0
                    }
                }

                Rectangle {
                    width: 30; height: 30; radius: 15
                    color: closeUpdateMa.containsMouse ? Qt.rgba(255, 255, 255, 0.12) : "transparent"
                    scale: closeUpdateMa.pressed ? 0.92 : (closeUpdateMa.containsMouse ? 1.08 : 1.0)
                    Behavior on scale { NumberAnimation { duration: 120 } }
                    Behavior on color { ColorAnimation { duration: 120 } }

                    Label {
                        anchors.centerIn: parent
                        text: "✕"
                        color: closeUpdateMa.containsMouse ? "#FFFFFF" : clrTxtDim
                        font.pixelSize: 13; font.bold: true
                    }
                    MouseArea {
                        id: closeUpdateMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: updateDialog.close()
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.leftMargin: 20
                Layout.rightMargin: 20
                Layout.preferredHeight: updateBodyCol.implicitHeight + 24
                radius: 14
                color: clrInput
                border.color: Qt.rgba(255, 255, 255, 0.08)
                border.width: 1

                ColumnLayout {
                    id: updateBodyCol
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 6

                    Label {
                        text: appBackend.uiTrigger, appBackend.getTextWithDefault("update_available_msg", "You have version {current}. Version {latest} is now available.")
                            .replace("{current}", updateDialog.plainVersion(updateDialog.currentVersion))
                            .replace("{latest}", updateDialog.plainVersion(updateDialog.latestVersion))
                        color: clrTxt
                        font.pixelSize: 13
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }
                    Label {
                        text: appBackend.uiTrigger, updateDialog.autoMode
                              ? appBackend.getTextWithDefault("update_available_auto", "Press Update now: LinguaNova downloads the new version, checks that the file is intact and installs it in the same folder. It reopens by itself when it finishes.")
                              : appBackend.getTextWithDefault("update_available_click", "Press the Download button to get the latest version. The download page will open in your browser.")
                        color: clrTxt2
                        font.pixelSize: 12
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }
                    ProgressBar {
                        id: updateProgressBar
                        Layout.fillWidth: true
                        visible: appBackend.updateDownloading
                        from: 0; to: 100
                        value: updateDialog.progress
                    }
                    Label {
                        visible: updateDialog.statusText.length > 0
                        text: updateDialog.statusText
                        color: updateDialog.autoFailed ? clrWarn : clrTxt2
                        font.pixelSize: 12
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 20
                Layout.rightMargin: 20
                Layout.bottomMargin: 20
                spacing: 12

                Button {
                    Layout.fillWidth: true; height: 40
                    scale: down ? 0.97 : (hovered ? 1.02 : 1.0)
                    transformOrigin: Item.Center
                    Behavior on scale { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
                    onClicked: {
                        if (appBackend.updateDownloading) appBackend.cancelAutoUpdate()
                        else updateDialog.close()
                    }

                    background: Rectangle {
                        radius: 12
                        color: parent.down ? Qt.rgba(255, 255, 255, 0.08) : (parent.hovered ? Qt.rgba(255, 255, 255, 0.05) : "transparent")
                        border.color: parent.hovered ? clrTxt2 : clrCardBorder
                        border.width: 1
                        Behavior on border.color { ColorAnimation { duration: 140 } }
                    }
                    contentItem: Label {
                        text: appBackend.uiTrigger, appBackend.updateDownloading
                              ? appBackend.getTextWithDefault("update_cancel_btn", "Cancel")
                              : appBackend.getTextWithDefault("factory_restart_later", "Later")
                        color: clrTxt2
                        font.pixelSize: 13
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }

                Button {
                    id: updateDownloadBtn
                    Layout.preferredWidth: 170; height: 40
                    enabled: !appBackend.updateDownloading
                    scale: down ? 0.97 : (hovered ? 1.02 : 1.0)
                    transformOrigin: Item.Center
                    Behavior on scale { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
                    onClicked: {
                        if (updateDialog.autoMode) {
                            updateDialog.statusText = ""
                            appBackend.startAutoUpdate()
                            return
                        }
                        if (updateDialog.releaseUrl) Qt.openUrlExternally(updateDialog.releaseUrl)
                        updateDialog.close()
                    }

                    background: Rectangle {
                        radius: 12
                        color: updateDownloadBtn.hovered ? "#D8FFA8" : clrAccent
                        gradient: Gradient {
                            orientation: Gradient.Horizontal
                            GradientStop { position: 0.0; color: updateDownloadBtn.hovered ? "#D8FFA8" : "#B8F36B" }
                            GradientStop { position: 1.0; color: updateDownloadBtn.hovered ? "#B8F36B" : "#A78BFA" }
                        }
                        Behavior on color { ColorAnimation { duration: 140 } }
                    }
                    contentItem: Label {
                        text: appBackend.uiTrigger, updateDialog.autoMode
                              ? "⟳ " + appBackend.getTextWithDefault("update_now_btn", "Update now")
                              : "⬇ " + appBackend.getTextWithDefault("update_download_btn", "Download")
                        color: "#0F0D0B"
                        font.bold: true
                        font.pixelSize: 13
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }
        }
    }

    Dialog {
        id: factoryResetDialog
        anchors.centerIn: parent
        width: Math.min(500, root.width * 0.85)
        padding: 0
        header: null
        footer: null
        modal: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        standardButtons: Dialog.NoButton

        enter: Transition {
            NumberAnimation { property: "opacity"; from: 0.0; to: 1.0; duration: 180; easing.type: Easing.OutCubic }
            NumberAnimation { property: "scale"; from: 0.94; to: 1.0; duration: 180; easing.type: Easing.OutCubic }
        }
        exit: Transition {
            NumberAnimation { property: "opacity"; from: 1.0; to: 0.0; duration: 140; easing.type: Easing.InQuad }
            NumberAnimation { property: "scale"; from: 1.0; to: 0.96; duration: 140; easing.type: Easing.InQuad }
        }

        Overlay.modal: Rectangle {
            color: Qt.rgba(0, 0, 0, 0.65)
        }

        background: Rectangle {
            color: clrCard
            radius: 18
            border.color: Qt.rgba(239, 68, 68, 0.45)
            border.width: 1.5
            clip: true

            Rectangle {
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                height: 3
                color: clrError
            }
        }

        contentItem: ColumnLayout {
            spacing: 16

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 20
                Layout.rightMargin: 18
                Layout.topMargin: 20
                spacing: 14

                Rectangle {
                    width: 40; height: 40; radius: 20
                    color: Qt.rgba(239, 68, 68, 0.15)
                    border.color: clrError; border.width: 1.5

                    Label {
                        anchors.centerIn: parent
                        text: "⚠️"
                        font.pixelSize: 20
                    }
                }

                ColumnLayout {
                    spacing: 2
                    Layout.fillWidth: true

                    Label {
                        text: appBackend.uiTrigger, appBackend.getTextWithDefault("factory_reset_title", "Fabrika Ayarlarına Sıfırla")
                        font.pixelSize: 17; font.bold: true; color: clrTxt
                    }
                    Label {
                        text: appBackend.uiTrigger, appBackend.getTextWithDefault("factory_reset_subtitle", "Kalıcı Sıfırlama İşlemi")
                        font.pixelSize: 12; color: clrError
                    }
                }

                Rectangle {
                    width: 30; height: 30; radius: 15
                    color: closeResetMa.containsMouse ? Qt.rgba(255, 255, 255, 0.12) : "transparent"
                    scale: closeResetMa.pressed ? 0.92 : (closeResetMa.containsMouse ? 1.08 : 1.0)
                    Behavior on scale { NumberAnimation { duration: 120 } }
                    Behavior on color { ColorAnimation { duration: 120 } }

                    Label {
                        anchors.centerIn: parent
                        text: "✕"
                        color: closeResetMa.containsMouse ? "#FFFFFF" : clrTxtDim
                        font.pixelSize: 13; font.bold: true
                    }
                    MouseArea {
                        id: closeResetMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: factoryResetDialog.close()
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.leftMargin: 20
                Layout.rightMargin: 20
                Layout.preferredHeight: resetBodyLbl.implicitHeight + 24
                radius: 14
                color: clrInput
                border.color: Qt.rgba(255, 255, 255, 0.08)
                border.width: 1

                Label {
                    id: resetBodyLbl
                    anchors.fill: parent
                    anchors.margins: 14
                    text: appBackend.uiTrigger, appBackend.getTextWithDefault("factory_reset_confirm", "Tüm ayarlar, API anahtarları, sözlük ve çeviri önbellekleri kalıcı olarak silinecek ve program ilk kurulduğu haline dönecek.\n\nEmin misiniz?")
                    color: clrTxt
                    wrapMode: Text.Wrap
                    font.pixelSize: 13
                    lineHeight: 1.35
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 20
                Layout.rightMargin: 20
                Layout.bottomMargin: 20
                spacing: 12

                Button {
                    Layout.fillWidth: true; height: 40
                    scale: down ? 0.97 : (hovered ? 1.02 : 1.0)
                    transformOrigin: Item.Center
                    Behavior on scale { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
                    onClicked: factoryResetDialog.close()

                    background: Rectangle {
                        radius: 12
                        color: parent.down ? Qt.rgba(255, 255, 255, 0.08) : (parent.hovered ? Qt.rgba(255, 255, 255, 0.05) : "transparent")
                        border.color: parent.hovered ? clrTxt2 : clrCardBorder
                        border.width: 1
                        Behavior on border.color { ColorAnimation { duration: 140 } }
                    }
                    contentItem: Label {
                        text: appBackend.uiTrigger, appBackend.getTextWithDefault("dialog_cancel", "İptal")
                        color: clrTxt2
                        font.pixelSize: 13
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }

                Button {
                    Layout.preferredWidth: 150; height: 40
                    scale: down ? 0.97 : (hovered ? 1.02 : 1.0)
                    transformOrigin: Item.Center
                    Behavior on scale { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
                    onClicked: {
                        factoryResetDialog.close()
                        if (appBackend.factoryReset())
                            factoryResetDoneDialog.open()
                    }

                    background: Rectangle {
                        radius: 12
                        color: parent.hovered ? "#DC2626" : clrError
                        Behavior on color { ColorAnimation { duration: 140 } }
                    }
                    contentItem: Label {
                        text: appBackend.uiTrigger, "🗑 " + appBackend.getTextWithDefault("factory_reset_btn", "Evet, Sıfırla")
                        color: "#FFFFFF"
                        font.bold: true
                        font.pixelSize: 13
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }
        }
    }

    Dialog {
        id: factoryResetDoneDialog
        anchors.centerIn: parent
        width: Math.min(480, root.width * 0.85)
        padding: 0
        header: null
        footer: null
        modal: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        standardButtons: Dialog.NoButton

        enter: Transition {
            NumberAnimation { property: "opacity"; from: 0.0; to: 1.0; duration: 180; easing.type: Easing.OutCubic }
            NumberAnimation { property: "scale"; from: 0.94; to: 1.0; duration: 180; easing.type: Easing.OutCubic }
        }
        exit: Transition {
            NumberAnimation { property: "opacity"; from: 1.0; to: 0.0; duration: 140; easing.type: Easing.InQuad }
            NumberAnimation { property: "scale"; from: 1.0; to: 0.96; duration: 140; easing.type: Easing.InQuad }
        }

        Overlay.modal: Rectangle {
            color: Qt.rgba(0, 0, 0, 0.65)
        }

        background: Rectangle {
            color: clrCard
            radius: 18
            border.color: Qt.rgba(16, 185, 129, 0.45)
            border.width: 1.5
            clip: true

            Rectangle {
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                height: 3
                color: clrSuccess
            }
        }

        contentItem: ColumnLayout {
            spacing: 16

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 20
                Layout.rightMargin: 18
                Layout.topMargin: 20
                spacing: 14

                Rectangle {
                    width: 40; height: 40; radius: 20
                    color: clrSuccessDim
                    border.color: clrSuccess; border.width: 1.5

                    Label {
                        anchors.centerIn: parent
                        text: "✅"
                        font.pixelSize: 20
                    }
                }

                ColumnLayout {
                    spacing: 2
                    Layout.fillWidth: true

                    Label {
                        text: appBackend.uiTrigger, cleanModalTitle(appBackend.getTextWithDefault("factory_reset_done_title", "Sıfırlama Tamamlandı"))
                        font.pixelSize: 17; font.bold: true; color: clrTxt
                    }
                    Label {
                        text: appBackend.uiTrigger, appBackend.getTextWithDefault("factory_reset_done_sub", "Ayarlar varsayılan duruma getirildi")
                        font.pixelSize: 12; color: clrTxt2
                    }
                }

                Rectangle {
                    width: 30; height: 30; radius: 15
                    color: closeResetDoneMa.containsMouse ? Qt.rgba(255, 255, 255, 0.12) : "transparent"
                    scale: closeResetDoneMa.pressed ? 0.92 : (closeResetDoneMa.containsMouse ? 1.08 : 1.0)
                    Behavior on scale { NumberAnimation { duration: 120 } }
                    Behavior on color { ColorAnimation { duration: 120 } }

                    Label {
                        anchors.centerIn: parent
                        text: "✕"
                        color: closeResetDoneMa.containsMouse ? "#FFFFFF" : clrTxtDim
                        font.pixelSize: 13; font.bold: true
                    }
                    MouseArea {
                        id: closeResetDoneMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: factoryResetDoneDialog.close()
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.leftMargin: 20
                Layout.rightMargin: 20
                Layout.preferredHeight: resetDoneBodyLbl.implicitHeight + 24
                radius: 14
                color: clrInput
                border.color: Qt.rgba(255, 255, 255, 0.08)
                border.width: 1

                Label {
                    id: resetDoneBodyLbl
                    anchors.fill: parent
                    anchors.margins: 14
                    text: appBackend.uiTrigger, appBackend.getTextWithDefault("factory_reset_done_msg", "Program ilk kurulduğu haline döndü. Temiz bir başlangıç için uygulamayı yeniden başlatın; bundan sonra yaptığınız ayarlar otomatik kaydedilecektir.")
                    color: clrTxt
                    wrapMode: Text.Wrap
                    font.pixelSize: 13
                    lineHeight: 1.35
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 20
                Layout.rightMargin: 20
                Layout.bottomMargin: 20
                spacing: 12

                Button {
                    Layout.fillWidth: true; height: 40
                    scale: down ? 0.97 : (hovered ? 1.02 : 1.0)
                    transformOrigin: Item.Center
                    Behavior on scale { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
                    onClicked: factoryResetDoneDialog.close()

                    background: Rectangle {
                        radius: 12
                        color: parent.down ? Qt.rgba(255, 255, 255, 0.08) : (parent.hovered ? Qt.rgba(255, 255, 255, 0.05) : "transparent")
                        border.color: parent.hovered ? clrTxt2 : clrCardBorder
                        border.width: 1
                        Behavior on border.color { ColorAnimation { duration: 140 } }
                    }
                    contentItem: Label {
                        text: appBackend.uiTrigger, appBackend.getTextWithDefault("factory_restart_later", "Daha Sonra")
                        color: clrTxt2
                        font.pixelSize: 13
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }

                Button {
                    id: factoryRestartBtn
                    Layout.preferredWidth: 180; height: 40
                    scale: down ? 0.97 : (hovered ? 1.02 : 1.0)
                    transformOrigin: Item.Center
                    Behavior on scale { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
                    onClicked: appBackend.restartApplication()

                    background: Rectangle {
                        radius: 12
                        color: factoryRestartBtn.hovered ? "#D8FFA8" : clrAccent
                        gradient: Gradient {
                            orientation: Gradient.Horizontal
                            GradientStop { position: 0.0; color: factoryRestartBtn.hovered ? "#D8FFA8" : "#B8F36B" }
                            GradientStop { position: 1.0; color: factoryRestartBtn.hovered ? "#B8F36B" : "#A78BFA" }
                        }
                        Behavior on color { ColorAnimation { duration: 140 } }
                    }
                    contentItem: Label {
                        text: appBackend.uiTrigger, "🔁 " + appBackend.getTextWithDefault("factory_restart_now", "Şimdi Yeniden Başlat")
                        color: "#0F0D0B"
                        font.bold: true
                        font.pixelSize: 13
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }
        }
    }

    // ── Glossary Dialogs ─────────────────────────────────────────────────
    GlossaryAddDialog {
        id: addGlossaryDialog
        clrCard: root.clrCard
        clrAccent: root.clrAccent
        clrAccent2: root.clrAccent2
        clrTxt: root.clrTxt
        clrTxt2: root.clrTxt2
        clrTxtDim: root.clrTxtDim
        clrInput: root.clrInput
        clrCardBorder: root.clrCardBorder
    }

    FileDialog {
        id: importGlossaryDialog
        title: appBackend.uiTrigger, appBackend.getTextWithDefault("glossary_dlg_import", "📥 Import Glossary")
        nameFilters: ["Glossary Files (*.json *.csv *.xlsx)", "All Files (*)"]
        onAccepted: {
            var path = appBackend.urlToPath(selectedFile.toString())
            appBackend.importGlossary(path)
        }
    }

    FileDialog {
        id: exportGlossaryDialog
        title: appBackend.uiTrigger, appBackend.getTextWithDefault("glossary_dlg_export", "📤 Export Glossary")
        fileMode: FileDialog.SaveFile
        nameFilters: ["JSON (*.json)", "CSV (*.csv)", "Excel (*.xlsx)"]
        onAccepted: {
            var path = appBackend.urlToPath(selectedFile.toString())
            appBackend.exportGlossary(path)
        }
    }
}
