package jp.ac.osaka_u.sdl.nil.usecase.cloneDetection

import io.reactivex.rxjava3.core.Flowable
import jp.ac.osaka_u.sdl.nil.entity.ClonePairResult
import jp.ac.osaka_u.sdl.nil.entity.Id
import jp.ac.osaka_u.sdl.nil.entity.TokenSequence
import jp.ac.osaka_u.sdl.nil.entity.toNgrams

class NormalCloneDetection(
    private val locatingPhase: Location,
    private val filteringPhase: Filtration,
    private val verifyingPhase: Verification,
    private val tokenSequences: List<TokenSequence>,
    private val gramSize: Int
) : CloneDetection {
    override fun exec(id: Id): Flowable<ClonePairResult> {
        val nGrams = tokenSequences[id].toNgrams(gramSize)
        return locatingPhase.locate(nGrams, id)
            .flatMap { candidate ->
                val (passesFiltration, nGramSim) = filteringPhase.filterWithSimilarity(nGrams.size, candidate)
                if (passesFiltration) {
                    Flowable.just(Pair(candidate.key.id, nGramSim))
                } else {
                    Flowable.empty()
                }
            }
            .flatMap { (candidateId: Int, nGramSim: Int) ->
                val (passesLCS, lcsSim) = verifyingPhase.verifyWithSimilarity(
                    tokenSequences[id], 
                    tokenSequences[candidateId]
                )
                if (passesLCS) {
                    Flowable.just(
                        ClonePairResult(
                            id1 = candidateId,
                            id2 = id,
                            nGramSimilarity = nGramSim,
                            lcsSimilarity = lcsSim
                        )
                    )
                } else {
                    Flowable.empty()
                }
            }
    }
}
