# In new Python
from io import TextIOWrapper
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.flight
import pyarrow.plasma as plasma
from multiprocessing import shared_memory
from contextlib import contextmanager
import time

def retrieve_sharedmemory(name: str) -> pa.Table:
    table_shm = shared_memory.SharedMemory(name=name)
    pa.ipc.open_stream(table_shm.buf).read_all()
    table_shm.close()

def retrieve_plasma(client, object_id: bytes) -> pa.Table:
    [buffer] = client.get_buffers([object_id])
    reader = pa.BufferReader(buffer)
    table = pa.ipc.open_stream(reader).read_all()
    for column in table:
        pc.sum(column)

def retrieve_flight(client) -> pa.Table:
    descriptor = pa.flight.FlightDescriptor.for_path("table")
    flight_into = client.get_flight_info(descriptor)
    reader = client.do_get(flight_into.endpoints[0].ticket)
    for chunk in reader:
        for col in chunk.data.columns:
            pc.sum(col)

@contextmanager
def timer(f: TextIOWrapper, name: str):
    start_time = time.time()
    yield None
    end_time = time.time()
    f.write(f'"{name}",{(end_time-start_time)}\n')

if __name__ == "__main__":
    n_iters = 10

    f = open("retrieve_results.csv", mode="w")

    plasma_client = plasma.connect("/tmp/plasma")
    object_id = plasma.ObjectID(20 * b"a")
    for i in range(n_iters):
        with timer(f, "plasma_import"):
            retrieve_plasma(plasma_client, object_id)
    
    # shared_memory_name = "table"
    # for i in range(n_iters):
    #     with timer(f, "sharedmemory_import"):
    #         retrieve_sharedmemory(shared_memory_name)
    
    location = "grpc+unix:///tmp/test.sock"
    flight_client = pa.flight.connect(location)
    for i in range(n_iters):
        with timer(f, "flight_export"):
            retrieve_flight(flight_client)
