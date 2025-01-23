import os
import time
from models import ConvexCodegenModel


def generate(input_dir: str, output_dir: str, model: ConvexCodegenModel):
    start = time.time()

    with open(f"{input_dir}/TASK.txt", "r") as f:
        task_description = f.read()

    files = model.generate(task_description)
    generated = sum(len(content) for content in files.values())

    project_dir = os.path.abspath(os.path.join(output_dir, "project"))
    os.makedirs(project_dir, exist_ok=True)

    for path, content in files.items():
        print(f"Writing {path}...")
        abs_file_path = os.path.abspath(os.path.join(project_dir, path))
        if not abs_file_path.startswith(project_dir):
            raise ValueError(f"File path {abs_file_path} is not underneath {project_dir}")

        os.makedirs(os.path.dirname(abs_file_path), exist_ok=True)

        with open(abs_file_path, "w") as f:
            f.write(content)
            generated += len(content)

    print(f"Generated {generated} bytes in {time.time() - start} seconds to {output_dir}")
