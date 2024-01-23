"""Convert a Transcriber TRS subtitle file into the WEBVTT format."""

import argparse
import datetime
import sys
from xml.etree import ElementTree


def format_time(time: str):
    """Convert ssss[.sss] into hh:mm:ss.sss format.

    :param time: Time code in seconds as extracted from the TRS input file
    :type time: str
    :returns: Time code infixed-length hh:mm:ss.sss format
    :rtype: str
    """
    time = "0" + str(datetime.timedelta(seconds=float(time)))[:11]
    if "." in time:
        # Add 1 or 2 zeros so the ms suffix has a length of 3
        return time + "0" * (12 - len(time))
    return time + ".000"


def generate_timestamp(start_time: str, end_time: str) -> str:
    """Generate a WEBTTV-format time stamp 'hh:mm:ss.sss --> hh:mm:ss.sss.'

    :param start_time: Time code in seconds as extracted from the TRS file
    :type start_time: str
    :param end_time: Time code in seconds as extracted from the TRS file
    :type end_time: str
    :returns: Time stamp in format hh:mm:ss.sss --> hh:mm:ss.sss
    :rtype: str
    """
    return "{0} --> {1}".format(format_time(start_time), format_time(end_time))


def convert(
    input_path: str,
    language: str = "",
    add_speakers: bool = False,
    preserve_noise: bool = False,
) -> str:
    """Read and parse input file.

    :param input_file: Path to the input TRS file.
    :type input_file: str
    :param language: Language code to add as a prefix
    :type language: str
    :param add_speakers: Prepend speaker names to lines
    :type add_speakers: bool
    :param noise: Preserve noise such as laughter or hesitation
    :type noise: bool
    :returns: Input file in WEBVTT format.
    :rtype: str
    """
    noise = {
        "COUGH": " <i>(coughs)</i> ",
        "EE-HESITATION": " <i>(hesitates)</i> ",
        "LAUGHTER": " <i>(laughs)</i> ",
        "LIP_SMACK": " <i>(smacks lips)</i> ",
        "LOUD_BREATH": " <i>(breaths loudly)</i> ",
        "NOISE": " <i>(noise)</i> ",
        "SILENCE": " <i>(silence)</i> ",
        "UH-HUH": " <i>(uh-huh)</i> ",
        "UNINTELLIGIBLE": " <i>(unintelligible)</i> ",
    }

    with open(input_path, "r", encoding="utf-8") as file:
        tree = ElementTree.parse(file)
        root = tree.getroot()

    speakers = {
        speaker.attrib["id"]: speaker.attrib["name"]
        for speaker in root.find("Speakers").iter("Speaker")
    }

    # Add file prefix
    vtt_lines = ["WEBVTT"]
    if language:
        vtt_lines.append("Language: {}".format(language))
    vtt_lines.append("")

    # Iterate the speaker turns
    for section in root.find("Episode").iter("Section"):
        for turn in section.iter("Turn"):
            speaker = speakers.get(turn.attrib.get("speaker", ""), "")
            speaker_prefix = "<v {}>".format(speaker)
            start_time = turn.attrib["startTime"]
            end_time = ""
            text = ""
            for annotation in turn.iter():
                # Parent node
                if annotation.tag == "Turn":
                    continue
                # New lines are added at synchronization points
                if annotation.tag == "Sync":
                    end_time = annotation.attrib["time"]
                    if text:
                        vtt_lines.append(generate_timestamp(start_time, end_time))
                        vtt_lines.append(add_speakers * speaker_prefix + text.strip())
                        vtt_lines.append("")
                        text = ""
                    text = text + annotation.tail.strip()
                    start_time = end_time
                # Events themselves are added only if preserve_noise == True
                elif annotation.tag == "Event":
                    if preserve_noise:
                        text = text + noise[annotation.attrib["desc"]]
                    text = text + annotation.tail.strip()
            # Handle text line at the end of turn
            if text:
                vtt_lines.append(generate_timestamp(start_time, turn.attrib["endTime"]))
                vtt_lines.append(add_speakers * speaker_prefix + text.strip())
                vtt_lines.append("")

    return "\n".join(vtt_lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert a TRS subtitle file to the WebVTT format."
    )
    parser.add_argument("input", help="Path to the input file")
    parser.add_argument(
        "-o",
        "--output",
        required=False,
        nargs="?",
        metavar="PATH",
        help="Write output to PATH instead of STDOUT",
    )
    parser.add_argument(
        "-l",
        "--language",
        required=False,
        nargs="?",
        metavar="LANG",
        help="Add 'Language: LANG' prefix to output",
    )
    parser.add_argument(
        "-s",
        "--speakers",
        required=False,
        action="store_true",
        help="Add speaker metadata to each line",
    )
    parser.add_argument(
        "-n",
        "--noise",
        required=False,
        action="store_true",
        help="Preserve noise such as laughter or silence",
    )
    args = parser.parse_args()

    vtt = convert(args.input, args.language, args.speakers, args.noise)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(vtt)
    else:
        sys.stdout.write(vtt)
