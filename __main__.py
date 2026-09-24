import os
import pulumi
import pulumi_docker as docker

RESOURCE_COUNT = int(
    os.getenv("BENCHMARK_RESOURCE_COUNT", "10")
)

image = docker.RemoteImage(
    "nginx-image",
    name="nginx:alpine",
    keep_locally=True,
)

for i in range(RESOURCE_COUNT):
    docker.Container(
        f"container-{i}",
        image=image.image_id,
        name=f"pulumi-benchmark-{i}",
    )

pulumi.export("resource_count", RESOURCE_COUNT)