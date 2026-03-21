package jp.ac.osaka_u.sdl.nil.usecase.cloneDetection

import io.reactivex.rxjava3.core.Flowable
import jp.ac.osaka_u.sdl.nil.entity.ClonePairResult
import jp.ac.osaka_u.sdl.nil.entity.Id
import jp.ac.osaka_u.sdl.nil.entity.TokenSequence
import jp.ac.osaka_u.sdl.nil.entity.toNgrams

class OptimizedCloneDetection(
    private val locatingPhase: Location,
    private val filteringPhase: Filtration,
    private val filtrationBasedVerificationPhase: Filtration,
    private val verifyingPhase: Verification,
    private val tokenSequences: List<TokenSequence>,
    private val gramSize: Int
) : CloneDetection {
    override fun exec(id: Id): Flowable<ClonePairResult> {
        val nGrams = tokenSequences[id].toNgrams(gramSize)
        return locatingPhase.locate(nGrams, id)
            .filter { filteringPhase.filter(nGrams.size, it) }
            .flatMap { candidate ->
                // N-gram similarity for verification phase (70%)
                val (passesNGramVerification, nGramVerificationSimilarity) = 
                    filtrationBasedVerificationPhase.filterWithSimilarity(nGrams.size, candidate)
                
                if (passesNGramVerification) {
                    // Passed N-gram verification, no need for LCS
                    Flowable.just(
                        ClonePairResult(
                            id1 = candidate.key.id,
                            id2 = id,
                            nGramSimilarity = nGramVerificationSimilarity,
                            lcsSimilarity = null
                        )
                    )
                } else {
                    // Need LCS verification
                    val (passesLCS, lcsSim) = verifyingPhase.verifyWithSimilarity(
                        tokenSequences[id], 
                        tokenSequences[candidate.key.id]
                    )
                    if (passesLCS) {
                        Flowable.just(
                            ClonePairResult(
                                id1 = candidate.key.id,
                                id2 = id,
                                nGramSimilarity = nGramVerificationSimilarity,
                                lcsSimilarity = lcsSim
                            )
                        )
                    } else {
                        Flowable.empty()
                    }
                }
            }
    }
}
