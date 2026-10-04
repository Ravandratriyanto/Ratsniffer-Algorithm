from __future__ import annotations 
import copy
from collections import Counter 
from chain import Blockchain, Block 

class Validator:
    def __init__(self, vid, difficulty=2, honest=True):
        self.vid = vid
        self.honest = honest 
        self.chain = Blockchain(difficulty=difficulty)
    def fingerprint(self):
        return tuple(b.hash for b in self.chain.chain)
    def vote(self, block):
        ok, _= self.chain.verify_chain()
        extends = block.prev_hash == self.chain.last.hash
        sound = block.compute_hash() == block.hash and block.hash.startswith(self.chain.target)
        return self.honest and ok and extends and sound 
    def commit(self, block):
        self.chain.chain.append(block)
class Consortium:
    def __init__(self, n=5, difficulty=2, quorum=None):
        self.validators = [Validator(f"v{i}", difficulty) for i in range(n)]
        self.quorum = quorum if quorum is not None else (2*n) //3 + 1
        self.signatures = {}
    def canonical(self):
        valid = [v for v in self.validators if v.chain.verify_chain()[0]]
        if not valid:
            return None 
        fp, count = Counter(v.fingerprint() for v in valid).most_common(1)[0]
        if count >= self.quorum:
            return next(v.chain for v in valid if v.fingerprint()==fp)
        return None 
    def propose(self, txns, proposer=0):
        p = self.validators[proposer]
        block = Block(index=len(p.chain.chain), txns=txns, prev_hash=p.chain.last.hash)
        p.chain._seal(block)
        votes = [v.vid for v in self.validators if v.vote(block)]
        if len(votes) >= self.quorum:
            for v in self.validators:
                v.commit(copy.deepcopy(block))
            self.signatures[block.hash] = votes
            return True, votes
        return False, votes