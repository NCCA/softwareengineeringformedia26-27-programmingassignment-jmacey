import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

ApplicationWindow {
    id: window
    required property QtObject backend
    visible: true
    width: 1040
    height: 800
    minimumWidth: 760
    minimumHeight: 640
    title: "Pedal training samples"
    color: "#171d26"
    palette.window: "#171d26"
    palette.windowText: "#eef2f6"
    palette.text: "#eef2f6"
    palette.base: "#222d3a"
    palette.button: "#2a3746"
    palette.buttonText: "#eef2f6"
    palette.highlight: "#50c9ad"
    palette.highlightedText: "#10251f"

    FolderDialog {
        id: sampleFolder
        title: "Choose a folder of input samples"
        onAccepted: window.backend.addSampleFolder(selectedFolder)
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 18

        Label { text: "Training sample setup"; font.pixelSize: 27; font.bold: true }
        Label { text: "Choose an input, describe the pedal and select the source audio."; color: "#a7b6c8" }

        GroupBox {
            title: "01 / Mixer input"
            Layout.fillWidth: true
            RowLayout {
                anchors.fill: parent
                ComboBox {
                    id: inputDevice
                    objectName: "inputDevice"
                    Layout.fillWidth: true
                    model: window.backend.devices
                    textRole: "name"
                    currentIndex: window.backend.selectedDeviceIndex
                    displayText: currentIndex < 0 ? "No input devices available" : currentText
                    onActivated: window.backend.selectDevice(currentIndex)
                    Accessible.name: "Mixer input device"
                }
                Label {
                    text: inputDevice.currentIndex < 0 ? "" :
                        window.backend.devices[inputDevice.currentIndex].channels + " channels · " +
                        window.backend.devices[inputDevice.currentIndex].sample_rate + " Hz"
                    color: "#a7b6c8"
                }
                Button { text: "Refresh"; onClicked: window.backend.refreshDevices() }
            }
        }

        GroupBox {
            title: "02 / Pedal controls"
            Layout.fillWidth: true
            Layout.preferredHeight: 265
            ColumnLayout {
                anchors.fill: parent
                RowLayout {
                    Label { text: "Number of knobs" }
                    SpinBox {
                        objectName: "controlCount"
                        from: 0; to: 16
                        value: window.backend.controls.length
                        onValueModified: window.backend.setControlCount(value)
                        Accessible.name: "Number of pedal controls"
                    }
                    Label { text: "Positions describe the physical pedal (0–100%)."; color: "#a7b6c8" }
                }
                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    contentWidth: controlRow.implicitWidth
                    Row {
                        id: controlRow
                        spacing: 16
                        Repeater {
                            model: window.backend.controls.length
                            ColumnLayout {
                                required property int index
                                readonly property var control: window.backend.controls[index]
                                width: 142
                                Dial {
                                    Layout.alignment: Qt.AlignHCenter
                                    Layout.preferredWidth: 100
                                    Layout.preferredHeight: 100
                                    from: 0; to: 1; stepSize: 0.01
                                    value: control.value
                                    onMoved: window.backend.setControlValue(index, value)
                                    Accessible.name: control.label
                                }
                                TextField {
                                    Layout.fillWidth: true
                                    text: control.label
                                    horizontalAlignment: Text.AlignHCenter
                                    selectByMouse: true
                                    maximumLength: 64
                                    onEditingFinished: window.backend.setControlLabel(index, text)
                                    Accessible.name: "Label for control " + (index + 1)
                                }
                                Label {
                                    Layout.alignment: Qt.AlignHCenter
                                    text: Math.round(control.value * 100) + "%"
                                    color: "#50c9ad"
                                }
                            }
                        }
                    }
                }
            }
        }

        GroupBox {
            title: "03 / Input samples"
            Layout.fillWidth: true
            Layout.fillHeight: true
            ColumnLayout {
                anchors.fill: parent
                RowLayout {
                    Button { text: "Add folder…"; onClicked: sampleFolder.open() }
                    Button { text: "Select all"; enabled: window.backend.samples.length > 0; onClicked: window.backend.selectAllSamples(true) }
                    Button { text: "Select none"; enabled: window.backend.samples.length > 0; onClicked: window.backend.selectAllSamples(false) }
                    Item { Layout.fillWidth: true }
                    Label { text: window.backend.selectedSampleCount + " / " + window.backend.samples.length + " selected" }
                    Button { text: "Clear"; enabled: window.backend.samples.length > 0; onClicked: window.backend.clearSamples() }
                }
                ListView {
                    id: sampleList
                    objectName: "sampleList"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    spacing: 4
                    model: window.backend.samples.length
                    ScrollBar.vertical: ScrollBar {}
                    delegate: CheckDelegate {
                        required property int index
                        readonly property var sample: window.backend.samples[index]
                        width: sampleList.width
                        text: sample.name + "    ·    " + sample.duration.toFixed(2) + " s    ·    " +
                              sample.channels + " ch    ·    " + sample.sample_rate + " Hz"
                        checked: sample.selected
                        onToggled: window.backend.selectSample(index, checked)
                        ToolTip.visible: hovered
                        ToolTip.text: sample.path
                    }
                    Label {
                        anchors.centerIn: parent
                        visible: sampleList.count === 0
                        text: "Add a folder of WAV, FLAC, AIFF or OGG samples to begin."
                        color: "#a7b6c8"
                    }
                }
            }
        }
        Label {
            Layout.fillWidth: true
            text: window.backend.message
            wrapMode: Text.WordWrap
            color: "#a7b6c8"
        }
    }
}
