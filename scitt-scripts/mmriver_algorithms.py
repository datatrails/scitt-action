"""
Selective copy of

https://github.com/robinbryce/draft-bryce-cose-merkle-mountain-range-proofs/blob/main/algorithms.py

Which is a reference implementation of

https://robinbryce.github.io/draft-bryce-cose-merkle-mountain-range-proofs/draft-bryce-cose-merkle-mountain-range-proofs.html


"""
from typing import List
import hashlib


def included_root(i: int, nodehash: bytes, proof: List[bytes]) -> bytes:
    """Apply the proof to nodehash to produce the implied root

    For a valid cose receipt of inclusion, using the returned root as the
    detached payload will result in a receipt message whose signature can be
    verified.

    Args:
        i (int): the mmr index where `nodehash` is located.
        nodehash (bytes): the value whose inclusion is being proven.
        proof (List[bytes]): the siblings required to produce `root` from `nodehash`.

    Returns:
        the root hash produced for `nodehash` using `path`
    """

    # set `root` to the value whose inclusion is to be proven
    root = nodehash

    # set g to the zero based height of i.
    g = index_height(i)

    # for each sibling in the proof
    for sibling in proof:
        # if the height of the entry immediately after i is greater than g, then
        # i is a right child.
        if index_height(i + 1) > g:
            # advance i to the parent. As i is a right child, the parent is at `i+1`
            i = i + 1
            # Set `root` to `H(i+1 || sibling || root)`
            root = hash_pospair64(i + 1, sibling, root)
        else:
            # Advance i to the parent. As i is a left child, the parent is at `i + (2^(g+1))`
            i = i + (2 << g)
            # Set `root` to `H(i+1 || root || sibling)`
            root = hash_pospair64(i + 1, root, sibling)

        # Set g to the height index above the current
        g = g + 1

    # Return the hash produced. If the path length was zero, the original nodehash is returned
    return root


def index_height(i: int) -> int:
    """Returns the 0 based height of the mmr entry indexed by i"""
    # convert the index to a position to take advantage of the bit patterns afforded
    pos = i + 1
    while not all_ones(pos):
        pos = pos - (most_sig_bit(pos) - 1)

    return pos.bit_length() - 1


def hash_pospair64(pos: int, a: bytes, b: bytes) -> bytes:
    """
    Compute the hash of  pos || a || b

    Args:
        pos (int): the 1-based position of an mmr node. If a, b are left and
            right children, pos should be the parent position.
        a (bytes): the first value to include in the hash
        b (bytes): the second value to include in the hash

    Returns:
        The value for the node identified by pos
    """
    h = hashlib.sha256()
    h.update(pos.to_bytes(8, byteorder="big", signed=False))
    h.update(a)
    h.update(b)
    return h.digest()


def most_sig_bit(pos) -> int:
    """Returns the mask for the the most significant bit in pos"""
    return 1 << (pos.bit_length() - 1)


def all_ones(pos) -> bool:
    """Returns true if all bits, starting with the most significant, are 1"""
    imsb = pos.bit_length() - 1
    mask = (1 << (imsb + 1)) - 1
    return pos == mask
