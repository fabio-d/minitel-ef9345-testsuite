import argparse
import PIL.Image
import PIL.ImageSequence


def do_pack(args: argparse.Namespace):
    inputs = [PIL.Image.open(path).convert("RGB") for path in args.input]
    if len(inputs) == 1:
        inputs[0].save(
            args.output,
            format="png",
        )
    else:
        inputs[0].save(
            args.output,
            format="png",
            append_images=inputs[1:],
            duration=args.duration,
            loop=0,
            save_all=True,
        )


def do_unpack(args: argparse.Namespace):
    input = PIL.Image.open(args.input)
    for i, img in enumerate(PIL.ImageSequence.all_frames(input)):
        img.convert("RGB").save(args.output % i)


def do_info(args: argparse.Namespace):
    for path in args.file:
        image = PIL.Image.open(path)
        size = f"{image.width}x{image.height}"
        if not hasattr(image, "n_frames"):
            print(f"{path}: {size} not animated")
        else:
            durations = []
            for i in range(image.n_frames):
                image.seek(i)
                durations.append(image.info.get("duration", None))
            print(f"{path}: {size} #{image.n_frames}", durations)


def main():
    parser = argparse.ArgumentParser()

    command = parser.add_subparsers(metavar="COMMAND", required=True)

    pack = command.add_parser("pack")
    pack.add_argument("output", metavar="output.png")
    pack.add_argument("input", metavar="input.png", nargs="+")
    pack.add_argument("-d", "--duration", default=500, metavar="MS", type=int)
    pack.set_defaults(func=do_pack)

    unpack = command.add_parser("unpack")
    unpack.add_argument("input", metavar="input.png")
    unpack.add_argument("output", metavar="output%d.png")
    unpack.set_defaults(func=do_unpack)

    info = command.add_parser("info")
    info.add_argument("file", metavar="file.png", nargs="*")
    info.set_defaults(func=do_info)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
