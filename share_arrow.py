from io import TextIOWrapper
import time
import pyarrow as pa
import pyarrow.flight
from multiprocessing import shared_memory
import pyarrow.plasma as plasma
from contextlib import contextmanager
import numpy as np

# TODO: show IPC file for comparison
# TODO: show Ray actor for comparison

def calculate_ipc_size(table: pa.Table) -> int:
    sink = pa.MockOutputStream()
    with pa.ipc.new_stream(sink, table.schema) as writer:
        writer.write_table(table)
    return sink.size()

def write_ipc_buffer(table: pa.Table) -> pa.Buffer:
    sink = pa.BufferOutputStream()

    with pa.ipc.new_stream(sink, table.schema) as writer:
        writer.write_table(table)

    return sink.getvalue()

def get_table(nrows: int):
    return pa.table({
        "x": np.random.random(nrows),
        "y": np.random.random(nrows),
    })

def export_to_shared_memory(name: str, table: pa.Table):
    size = calculate_ipc_size(table)
    shm = shared_memory.SharedMemory(create=True, name=name, size=size)

    stream = pa.FixedSizeBufferWriter(pa.py_buffer(shm.buf))
    with pa.RecordBatchStreamWriter(stream, table.schema) as writer:
        writer.write_table(table)

    return shm

def clear_shared_memory(name: str):
    try:
        shm = shared_memory.SharedMemory(name=name)
        shm.unlink()
    except:
        pass

def export_to_plasma(client, object_id: bytes, table: pa.Table):
    size = calculate_ipc_size(table)
    buffer = client.create(object_id, size)
    stream = pa.FixedSizeBufferWriter(buffer)
    with pa.RecordBatchStreamWriter(stream, table.schema) as writer:
        writer.write_table(table)

    client.seal(object_id)

def clear_plasma(client, object_id: bytes):
    client.delete([object_id])

def export_to_flight(client, table: pa.Table):
    descriptor = pa.flight.FlightDescriptor.for_path("table")
    writer, _ = client.do_put(descriptor, table.schema)
    writer.write_table(table)
    writer.close()
    

@contextmanager
def timer(f: TextIOWrapper, name: str, size: int):
    start_time = time.time()
    yield None
    end_time = time.time()
    f.write(f'"{name}",{(end_time-start_time)},{size}\n')


if __name__ == "__main__":
    n_iters = 10
    n_rows = 100_000_000
    table = get_table(n_rows)

    f = open("share_results.csv", mode="w")

    # Warm up the memory pool, so all runs are comparable
    buf = write_ipc_buffer(table)
    del buf

    buffer_size = calculate_ipc_size(table)

    # First, do plasma
    plasma_client = plasma.connect("/tmp/plasma")
    object_id = plasma.ObjectID(20 * b"a")
    for i in range(n_iters):
        clear_plasma(plasma_client, object_id)
        with timer(f, "plasma_export", buffer_size):
            export_to_plasma(plasma_client, object_id, table)
    
    # Then, do shared memory
    shared_memory_name = "table"
    for i in range(n_iters):
        clear_shared_memory(shared_memory_name)
        with timer(f, "sharedmemory_export", buffer_size):
            export_to_shared_memory(shared_memory_name, table)

    # Finally, flight
    location = "grpc+unix:///tmp/test.sock"
    flight_client = pa.flight.connect(location)
    for i in range(n_iters):
        # More graceful way to collect all the results?
        list(flight_client.do_action("clear"))
        with timer(f, "flight_export", buffer_size):
            export_to_flight(flight_client, table)

    # We need to disconnect, since only one client can connection to a Flight
    # server at a time when using the 
    # flight_client.close()
    # del flight_client

    f.close()
    print("ready!")

    while True:
        time.sleep(10)