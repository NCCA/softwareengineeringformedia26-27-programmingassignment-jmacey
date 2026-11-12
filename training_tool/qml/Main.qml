import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

ApplicationWindow {
    id: window
    required property QtObject backend
    visible: true
    width: 1040
    height: 1000
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

    onClosing: window.backend.shutdown()

    FolderDialog {
        id: recordingFolder
        title: "Choose where to save this training run"
        onAccepted: window.backend.prepareRun(selectedFolder)
    }

    ScrollView {
        id: page
        anchors.fill: parent
        anchors.margins: 24
        contentWidth: availableWidth
        clip: true
        ColumnLayout {
            width: page.availableWidth
            spacing: 18

            Label {
                text: "Training sample setup"
                font.pixelSize: 27
                font.bold: true
            }
            Label {
                text: "Choose an input, describe the pedal and select the source audio."
                color: "#a7b6c8"
            }

            GroupBox {
                title: "01 / Audio routing"
                enabled: !window.backend.runActive
                Layout.fillWidth: true
                ColumnLayout {
                    anchors.fill: parent
                    RowLayout {
                        Label {
                            text: "Pedal return"
                        }
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
                            text: inputDevice.currentIndex < 0 ? "" : window.backend.devices[inputDevice.currentIndex].channels + " channels · " + window.backend.devices[inputDevice.currentIndex].sample_rate + " Hz"
                            color: "#a7b6c8"
                        }
                        Button {
                            text: "Refresh"
                            onClicked: window.backend.refreshDevices()
                        }
                    }
                    RowLayout {
                        Label {
                            text: "Return channel"
                        }
                        SpinBox {
                            from: 1
                            to: inputDevice.currentIndex < 0 ? 1 : window.backend.devices[inputDevice.currentIndex].channels
                            value: window.backend.returnChannel
                            onValueModified: window.backend.setReturnChannel(value)
                        }
                        Label {
                            text: "Playback output"
                        }
                        ComboBox {
                            Layout.fillWidth: true
                            model: window.backend.outputs
                            textRole: "name"
                            currentIndex: window.backend.selectedOutputIndex
                            displayText: currentIndex < 0 ? "No playback output available" : currentText
                            onActivated: window.backend.selectOutput(currentIndex)
                        }
                    }
                    Label {
                        text: "Route playback channels 1/2 to the pedal input, and the pedal return to the selected input channel."
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                        color: "#a7b6c8"
                    }
                }
            }

            GroupBox {
                title: "02 / Pedal controls"
                Layout.fillWidth: true
                Layout.preferredHeight: 315
                ColumnLayout {
                    anchors.fill: parent
                    RowLayout {
                        Label {
                            text: "Number of knobs"
                        }
                        SpinBox {
                            enabled: !window.backend.runActive
                            objectName: "controlCount"
                            from: 0
                            to: 16
                            value: window.backend.controls.length
                            onValueModified: window.backend.setControlCount(value)
                            Accessible.name: "Number of pedal controls"
                        }
                        Label {
                            text: "Positions describe the physical pedal (0–100%)."
                            color: "#a7b6c8"
                        }
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
                                        enabled: !window.backend.runActive
                                        from: 0
                                        to: 1
                                        stepSize: 0.01
                                        value: control.value
                                        onMoved: window.backend.setControlValue(index, value)
                                        Accessible.name: control.label
                                    }
                                    TextField {
                                        Layout.fillWidth: true
                                        enabled: !window.backend.runActive
                                        text: control.label
                                        horizontalAlignment: Text.AlignHCenter
                                        selectByMouse: true
                                        maximumLength: 64
                                        onEditingFinished: window.backend.setControlLabel(index, text)
                                        Accessible.name: "Label for control " + (index + 1)
                                    }
                                    RowLayout {
                                        Label {
                                            text: "Steps"
                                        }
                                        SpinBox {
                                            objectName: "controlSteps" + index
                                            enabled: !window.backend.runActive
                                            from: 2
                                            to: 101
                                            value: control.steps
                                            onValueModified: window.backend.setControlSteps(index, value)
                                            Accessible.name: "Positions for " + control.label
                                        }
                                    }
                                    Label {
                                        Layout.alignment: Qt.AlignHCenter
                                        text: (control.value * 100).toFixed(1) + "%"
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
                enabled: !window.backend.runActive
                Layout.fillWidth: true
                Layout.preferredHeight: 210
                ColumnLayout {
                    anchors.fill: parent
                    RowLayout {
                        Button {
                            text: "Add folder…"
                            onClicked: sampleFolder.open()
                        }
                        Button {
                            text: "Select all"
                            enabled: window.backend.samples.length > 0
                            onClicked: window.backend.selectAllSamples(true)
                        }
                        Button {
                            text: "Select none"
                            enabled: window.backend.samples.length > 0
                            onClicked: window.backend.selectAllSamples(false)
                        }
                        Item {
                            Layout.fillWidth: true
                        }
                        Label {
                            text: window.backend.selectedSampleCount + " / " + window.backend.samples.length + " selected"
                        }
                        Button {
                            text: "Clear"
                            enabled: window.backend.samples.length > 0
                            onClicked: window.backend.clearSamples()
                        }
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
                            text: sample.name + "    ·    " + sample.duration.toFixed(2) + " s    ·    " + sample.channels + " ch    ·    " + sample.sample_rate + " Hz"
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
            GroupBox {
                title: "04 / Guided recording"
                Layout.fillWidth: true
                ColumnLayout {
                    anchors.fill: parent
                    Label {
                        text: window.backend.planSize + " x " + window.backend.selectedSampleCount + " selected samples. Steps include 0% and 100%."
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                    Label {
                        objectName: "trainingSummary"
                        text: window.backend.trainingSummary
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                        color: "#50c9ad"
                    }
                    RowLayout {
                        Button {
                            text: "Prepare run..."
                            enabled: !window.backend.runActive && !window.backend.recording
                            onClicked: recordingFolder.open()
                        }
                        Button {
                            objectName: "recordBatch"
                            text: "Pedal set: record batch"
                            enabled: window.backend.runActive && !window.backend.recording
                            onClicked: window.backend.recordBatch()
                        }
                        Button {
                            text: "Pause"
                            enabled: window.backend.recording
                            onClicked: window.backend.pauseRecording()
                        }
                        Button {
                            text: "End run"
                            enabled: window.backend.runActive && !window.backend.recording
                            onClicked: window.backend.endRun()
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
}
