import m5
from m5.objects import *
from m5.util import addToPath


# Add the common scripts to our path
addToPath('../configs/common')

# Import the SE workload module
from common import Options

@contextlib.contextmanager
def redirect_stdout(filename):
    original_stdout = sys.stdout
    with open(filename, 'w') as file:
        sys.stdout = file
        try:
            yield
        finally:
            sys.stdout = original_stdout

# Setting up system configuration
def create_system(cpu_type, num_threads=1, issue_width=1, branch_prediction=None):
    sys = System()

    # Set up the clock and voltage domains
    sys.clk_domain = SrcClockDomain()
    sys.clk_domain.clock = '1GHz'
    sys.clk_domain.voltage_domain = VoltageDomain()

    # Setting up the memory bus
    sys.membus = SystemXBar()

    # Creating CPU based configuration
    if cpu_type == 'MinorCPU':
        sys.cpu = MinorCPU()
        sys.cpu.fetchWidth = 1
        sys.cpu.decodeWidth = 1
        sys.cpu.executeWidth = 1
        sys.cpu.memoryWidth = 1
        sys.cpu.commitWidth = 1
    elif cpu_type == 'DerivO3CPU':
        sys.cpu = DerivO3CPU()
        sys.cpu.fetchWidth = issue_width
        sys.cpu.decodeWidth = issue_width
        sys.cpu.issueWidth = issue_width
        sys.cpu.executeWidth = issue_width
        sys.cpu.commitWidth = issue_width
        sys.cpu.numThreads = num_threads
    else:
        raise ValueError("Unsupported CPU type")

    # Setting up branch predictors
    if branch_prediction:
        sys.cpu.branchPred = branch_prediction

    # Setting up memory system
    sys.mem_mode = 'timing'
    sys.mem_ranges = [AddrRange('512MB')]
    sys.mem_ctrl = MemCtrl()
    sys.mem_ctrl.dram = DDR3_1600_8x8()
    sys.mem_ctrl.dram.range = sys.mem_ranges[0]
    sys.mem_ctrl.port = sys.membus.mem_side_ports

    # Connecting the CPU to the memory bus
    sys.cpu.icache_port = sys.membus.cpu_side_ports
    sys.cpu.dcache_port = sys.membus.cpu_side_ports

    # Setting up interrupts and workload
    sys.cpu.createInterruptController()
    binary = os.path.join(m5.options.outdir, 'tests', 'test-progs', 'hello', 'bin', 'x86', 'linux', 'hello')
    sys.workload = SEWorkload.init_compatible(binary)
    process = Process()
    process.cmd = [binary]
    sys.cpu.workload = process
    sys.cpu.createThreads()

    # Setting up the system port
    sys.system_port = sys.membus.cpu_side_ports

    return sys

# Main function to run the simulation
def run_simulation(cpu_type, num_threads=1, issue_width=1, branch_prediction=None):
    sys = create_system(cpu_type, num_threads, issue_width, branch_prediction)

    # Set up root and instantiate the system
    root = Root(full_system=False, system=sys)
    m5.instantiate()

    print("Starting simulation...")
    exit_event = m5.simulate()

    # Collect stats
    print(f"Simulation ended at tick {m5.curTick()} because {exit_event.getCause()}")
    print("Collecting stats...")
    m5.stats.dump()
    m5.stats.reset()

    # Display key metrics
    ipc = sys.cpu.ipc
    instructions = sys.cpu.numInsts
    cycles = sys.cpu.numCycles
    print(f"Instructions committed: {instructions}")
    print(f"Instructions per Cycle: {ipc}")
    print(f"Total cycles: {cycles}")

    m5.stats.reset()
    m5.stats.dump()

# Run configurations for different parts of the assignment
if __name__ == "__m5_main__":
    with redirect_stdout("output.txt"):
        # Basic Pipeline Simulation
        print("Basic pipeline simulation...")
        run_simulation(cpu_type='MinorCPU')

        # Impact of Branch Prediction
        print("Simulation with branch prediction...")
        run_simulation(cpu_type='MinorCPU', branch_prediction=BiModeBP())

        # Multiple Issue Simulation (Superscalar)
        print("Superscalar configuration...")
        run_simulation(cpu_type='DerivO3CPU', issue_width=2)

        # Multithreading (SMT)
        print("SMT configuration with 2 threads...")
        run_simulation(cpu_type='DerivO3CPU', issue_width=2, num_threads=2)

    print("Simulation results have been written to output.txt")
