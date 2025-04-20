from .main import main
from evaluation.utils.logging import setup_logger
import sys

if __name__ == "__main__":
    setup_logger(name="evaluation")
    main(sys.argv[1:])
