# In new Python
import pyarrow as pa
import pyarrow.flight
import pyarrow.plasma as plasma
from multiprocessing import shared_memory
from contextlib import contextmanager
import time

def retrieve_sharedmemory(name: str) -> pa.Table:
    # This is annoying
    table_shm = shared_memory.SharedMemory(name=name)
    pa.ipc.open_stream(table_shm.buf).read_all()
    table_shm.close()

def retrieve_plasma(client, object_id: bytes) -> pa.Table:
    [buffer] = client.get_buffers([object_id])
    reader = pa.BufferReader(buffer)
    pa.ipc.open_stream(reader).read_all()

def retrieve_flight(client) -> pa.Table:
    descriptor = pa.flight.FlightDescriptor.for_path("table")
    flight_into = client.get_flight_info(descriptor)
    reader = client.do_get(flight_into.endpoints[0].ticket)
    reader.read_all()

@contextmanager
def timer(name: str):
    start_time = time.time()
    yield None
    end_time = time.time()
    print(f'"{name}",{(end_time-start_time)}')

if __name__ == "__main__":
    n_iters = 10

    plasma_client = plasma.connect("/tmp/plasma")
    object_id = plasma.ObjectID(20 * b"a")
    for i in range(n_iters):
        with timer("plasma_import"):
            retrieve_plasma(plasma_client, object_id)
    
    # shared_memory_name = "table"
    # for i in range(n_iters):
    #     with timer("sharedmemory_import"):
    #         retrieve_sharedmemory(shared_memory_name)
    
    location = "grpc+unix:///tmp/output.sock"
    flight_client = pa.flight.connect(location)
    breakpoint()
    for i in range(n_iters):
        with timer("flight_export"):
            retrieve_flight(flight_client)