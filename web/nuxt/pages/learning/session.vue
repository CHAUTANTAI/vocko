<template>
  <div>
    <div class="flex flex-wrap items-center gap-4">
      <NuxtLink to="/deck" class="text-sm text-slate-400 hover:text-emerald-400"
        >← Decks</NuxtLink
      >
      <NuxtLink
        to="/learning/history"
        class="text-sm text-slate-400 hover:text-emerald-400"
        >Study history</NuxtLink
      >
    </div>

    <div
      v-if="!deckId"
      class="mt-8 rounded-xl border border-amber-900/50 bg-amber-950/30 p-6 text-center"
    >
      <p class="text-amber-200/90">Choose a deck to study.</p>
      <NuxtLink
        to="/deck"
        class="mt-4 inline-block rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500"
      >
        Go to decks
      </NuxtLink>
    </div>

    <div v-else class="mt-6">
      <div class="flex flex-wrap items-baseline justify-between gap-2">
        <h2 class="text-xl font-semibold text-white">Study session</h2>
        <p
          v-if="sessionId && sessionAnswered > 0 && !isSelfGradeSession"
          class="text-sm text-slate-400"
        >
          Score: {{ sessionCorrect }} / {{ sessionAnswered }} correct
        </p>
      </div>
      <p v-if="!isSelfGradeSession" class="mt-1 text-sm text-slate-400">
        Exact match (case insensitive), one typo accepted, or AI grading if
        configured.
      </p>
      <p v-else class="mt-1 text-sm text-slate-400">
        Self-grade: rate how well you remember each card (no typing). Full deck,
        then review unsure or forgotten cards or the whole set again.
      </p>

      <div v-if="!isSelfGradeSession" class="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          class="rounded-lg px-3 py-1.5 text-sm"
          :class="
            mode === 'learn'
              ? 'bg-emerald-600 text-white'
              : 'border border-slate-600 text-slate-300 hover:bg-slate-800'
          "
          :disabled="!!sessionId"
          @click="mode = 'learn'"
        >
          Learn
        </button>
        <button
          type="button"
          class="rounded-lg px-3 py-1.5 text-sm"
          :class="
            mode === 'review'
              ? 'bg-emerald-600 text-white'
              : 'border border-slate-600 text-slate-300 hover:bg-slate-800'
          "
          :disabled="!!sessionId"
          @click="mode = 'review'"
        >
          Review due
        </button>
      </div>
      <div v-else class="mt-4">
        <span
          class="inline-flex rounded-lg border border-emerald-800/60 bg-emerald-950/30 px-3 py-1.5 text-sm text-emerald-200/90"
        >
          Self-grade mode
        </span>
      </div>

      <p
        v-if="deckEmptyBlocked && !sessionId"
        class="mt-4 rounded-lg border border-amber-900/40 bg-amber-950/25 px-3 py-2 text-sm text-amber-100/90"
      >
        This deck has no cards yet. Add cards in the deck editor, then start a
        session.
        <NuxtLink
          :to="`/deck/${deckId}`"
          class="ml-1 font-medium text-emerald-400 underline hover:text-emerald-300"
        >
          Open deck
        </NuxtLink>
      </p>

      <label
        v-if="!sessionId && !isSelfGradeSession"
        class="mt-3 flex cursor-pointer select-none items-start gap-2 text-sm text-slate-400"
      >
        <input
          v-model="smartQueue"
          type="checkbox"
          class="mt-0.5 rounded border-slate-600 bg-slate-900 text-emerald-600 focus:ring-emerald-500/40"
        />
        <span>
          <span class="text-slate-300">{{ smartQueueTitle }}</span>
          <span
            v-if="mode === 'learn' && smartQueue"
            class="mt-1 block text-xs leading-relaxed text-slate-500"
          >
            Weak = due cards with tags you miss often or &ldquo;hard&rdquo;
            difficulty; new = no reviews yet; easy = due + high grades recently
            + stable ease. Target ~70/20/10 when enough cards exist; the server
            may add more via round-robin or random fill.
          </span>
          <span
            v-else-if="mode === 'review' && smartQueue"
            class="mt-1 block text-xs leading-relaxed text-slate-500"
          >
            Only <strong class="font-medium text-slate-400">due</strong> cards.
            Order: weak tags / hard bucket first, then by due date. This is
            <em>not</em> the 70/20/10 learn mix.
          </span>
        </span>
      </label>

      <label
        v-if="!sessionId"
        class="mt-3 flex cursor-pointer select-none items-start gap-2 text-sm text-slate-400"
      >
        <input
          v-model="autoAudio"
          type="checkbox"
          class="mt-0.5 rounded border-slate-600 bg-slate-900 text-emerald-600 focus:ring-emerald-500/40"
        />
        <span>
          <span class="text-slate-300">Auto audio</span>
          <span class="mt-1 block text-xs leading-relaxed text-slate-500">
            When on, each new vocab prompt is spoken automatically (English).
            You can always tap the speaker on the card to replay.
          </span>
        </span>
      </label>

      <div v-if="!sessionId" class="mt-6">
        <button
          type="button"
          class="rounded-lg bg-emerald-600 px-5 py-2.5 font-medium text-white hover:bg-emerald-500"
          @click="startSession"
        >
          Start session
        </button>
        <p v-if="sessionError" class="mt-2 text-sm text-red-400">
          {{ sessionError }}
        </p>
      </div>

      <p
        v-if="sessionId && queueMetaLine"
        class="mt-3 rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2 text-xs leading-relaxed text-slate-400"
      >
        {{ queueMetaLine }}
      </p>

      <div v-if="sessionId" class="mt-6">
        <div
          v-if="selfRoundBreak"
          class="rounded-xl border border-slate-700 bg-slate-900/60 p-6 text-center"
        >
          <p class="text-sm font-medium text-emerald-400/90">Round complete</p>
          <p class="mt-2 text-xs text-slate-500">
            Round index: {{ selfRoundBreak.roundIndex }}
          </p>
          <dl
            class="mx-auto mt-4 grid max-w-xs grid-cols-3 gap-2 text-sm text-slate-300"
          >
            <div
              class="rounded-lg border border-slate-800 bg-slate-950/50 px-2 py-2"
            >
              <dt class="text-[10px] uppercase text-slate-500">Know well</dt>
              <dd class="text-lg font-semibold text-white">
                {{ selfRoundBreak.breakdown.known }}
              </dd>
            </div>
            <div
              class="rounded-lg border border-slate-800 bg-slate-950/50 px-2 py-2"
            >
              <dt class="text-[10px] uppercase text-slate-500">Unsure</dt>
              <dd class="text-lg font-semibold text-amber-200/90">
                {{ selfRoundBreak.breakdown.unsure }}
              </dd>
            </div>
            <div
              class="rounded-lg border border-slate-800 bg-slate-950/50 px-2 py-2"
            >
              <dt class="text-[10px] uppercase text-slate-500">Forgot</dt>
              <dd class="text-lg font-semibold text-red-300/90">
                {{ selfRoundBreak.breakdown.forgot }}
              </dd>
            </div>
          </dl>
          <p class="mt-4 text-xs text-slate-500">
            Review cards you marked Unsure or Forgot, or run the full deck
            again.
          </p>
          <div class="mt-6 flex flex-wrap justify-center gap-3">
            <button
              type="button"
              class="rounded-lg bg-amber-600 px-4 py-2 text-sm font-medium text-white hover:bg-amber-500 disabled:cursor-not-allowed disabled:opacity-50"
              :disabled="continueRoundLoading"
              @click="continueSelfRound('weak')"
            >
              Review unsure + forgot
            </button>
            <button
              type="button"
              class="rounded-lg border border-slate-600 px-4 py-2 text-sm text-slate-200 hover:bg-slate-800 disabled:opacity-50"
              :disabled="continueRoundLoading"
              @click="continueSelfRound('all')"
            >
              Review full deck
            </button>
            <button
              type="button"
              class="rounded-lg border border-slate-600 px-4 py-2 text-sm text-slate-400 hover:bg-slate-800"
              :disabled="continueRoundLoading"
              @click="finishSelfGradeSession"
            >
              End session
            </button>
          </div>
          <p v-if="continueRoundError" class="mt-3 text-sm text-red-400">
            {{ continueRoundError }}
          </p>
        </div>
        <div v-else-if="question" class="w-full space-y-3">
          <div
            v-if="
              isSelfGradeSession &&
              sessionId &&
              question &&
              selfGradeRoundTotal > 0
            "
            class="w-full"
            role="progressbar"
            :aria-valuenow="selfGradeCompletedInRound"
            aria-valuemin="0"
            :aria-valuemax="selfGradeRoundTotal"
            aria-label="Round progress"
          >
            <div class="h-2 w-full overflow-hidden rounded-full bg-slate-800">
              <div
                class="h-full rounded-full bg-emerald-500 transition-[width] duration-300 ease-out"
                :style="{ width: `${selfGradeProgressPct}%` }"
              />
            </div>
          </div>
          <div class="relative">
            <div
              v-if="!isSelfGradeSession"
              class="absolute right-2 top-2 z-20 flex flex-col gap-2 rounded-lg border border-slate-700/80 bg-slate-900/90 px-2 py-1.5 text-xs text-slate-300"
            >
              <div class="flex cursor-pointer select-none items-center gap-2">
                <span>Auto next</span>
                <button
                  type="button"
                  role="switch"
                  :aria-checked="autoAdvance"
                  class="relative h-5 w-9 rounded-full transition-colors"
                  :class="autoAdvance ? 'bg-emerald-600' : 'bg-slate-600'"
                  @click="autoAdvance = !autoAdvance"
                >
                  <span
                    class="absolute top-0.5 h-4 w-4 rounded-full bg-white transition-transform"
                    :class="autoAdvance ? 'left-4' : 'left-0.5'"
                  />
                </button>
              </div>
            </div>
            <ClientOnly>
              <div
                v-motion
                :key="question.card_id"
                :initial="{ opacity: 0, y: 8 }"
                :enter="{ opacity: 1, y: 0, transition: { duration: 280 } }"
                class="rounded-xl border border-slate-700 shadow-lg [perspective:1200px]"
              >
                <button
                  type="button"
                  class="relative w-full min-h-[11rem] rounded-xl text-left outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/60 disabled:cursor-default"
                  :disabled="!canFlipCard"
                  :class="canFlipCard ? 'cursor-pointer' : 'cursor-default'"
                  :aria-label="
                    isSelfGradeSession
                      ? cardFlipped
                        ? 'Flip to prompt'
                        : 'Flip to peek answer'
                      : canFlipCard
                        ? 'Flip card to see answer'
                        : 'Card prompt'
                  "
                  @click="toggleCardFlip"
                >
                  <div
                    class="relative h-full min-h-[11rem] w-full transition-transform duration-500 ease-out"
                    :style="{
                      transformStyle: 'preserve-3d',
                      transform: cardFlipped
                        ? 'rotateY(180deg)'
                        : 'rotateY(0deg)',
                    }"
                  >
                    <div
                      class="absolute inset-0 flex flex-col justify-center rounded-xl border border-slate-700 bg-gradient-to-br from-slate-900 to-slate-950 p-8 pt-12 text-center shadow-inner [backface-visibility:hidden]"
                    >
                      <button
                        v-if="frontSpeechAvailable"
                        type="button"
                        class="absolute left-3 top-3 z-10 rounded-full border border-slate-600/80 bg-slate-800/90 p-2 text-slate-300 outline-none hover:bg-slate-700/90 hover:text-white focus-visible:ring-2 focus-visible:ring-emerald-500/60"
                        aria-label="Speak prompt"
                        @click.stop="playFrontSpeech(question)"
                      >
                        <Volume2 class="h-5 w-5" />
                      </button>
                      <p class="text-xs uppercase tracking-wide text-slate-500">
                        Prompt
                      </p>
                      <p class="mt-3 text-xl font-medium text-white">
                        {{ questionFront }}
                      </p>
                      <p
                        v-if="
                          question?.card_type === 'vocab' &&
                          question.part_of_speech
                        "
                        class="mt-2 text-sm font-medium text-slate-500"
                      >
                        {{ partOfSpeechDisplayLabel(question.part_of_speech) }}
                      </p>
                      <p
                        v-if="canFlipCard || isSelfGradeSession"
                        class="mt-4 text-xs text-slate-500"
                      >
                        {{
                          isSelfGradeSession
                            ? "Tap card to peek the answer"
                            : "Tap card to see the answer"
                        }}
                      </p>
                    </div>
                    <div
                      class="absolute inset-0 flex flex-col justify-center rounded-xl border border-emerald-900/40 bg-gradient-to-br from-slate-900 to-emerald-950/30 p-8 pt-12 text-center shadow-inner [backface-visibility:hidden] [transform:rotateY(180deg)]"
                    >
                      <div
                        v-if="
                          isSelfGradeSession &&
                          (question.card_type ||
                            question.part_of_speech ||
                            peekSelfGradePronunciations.length ||
                            peekSelfGradeMedia.length ||
                            peekSelfGradeNoteDisplay ||
                            peekSelfGradeExampleDisplay)
                        "
                        class="mt-4 rounded-2xl border border-slate-800 bg-slate-950/95 p-4 text-left text-sm text-slate-300"
                      >
                        <p
                          class="text-xs uppercase tracking-wide text-emerald-500/80 text-center w-full"
                        >
                          Answer
                        </p>
                        <div class="mt-3 mb-4 w-full flex justify-center">
                          <template v-if="isSelfGradeSession">
                            <div
                              v-if="peekSelfGradeBackHtml"
                              class="inline-block max-w-full text-left text-xl font-medium text-emerald-50 prose prose-invert prose-sm prose-p:my-1 prose-li:my-0.5"
                              v-html="peekSelfGradeBackHtml"
                            ></div>
                            <p
                              v-else
                              class="text-xl font-medium text-emerald-50"
                            >
                              —
                            </p>
                          </template>
                          <template v-else>
                            <div
                              v-if="revealedBackDisplay"
                              class="inline-block max-w-full text-left text-xl font-medium text-emerald-50 prose prose-invert prose-sm prose-p:my-1 prose-li:my-0.5"
                              v-html="revealedBackDisplay"
                            ></div>
                            <p
                              v-else
                              class="text-xl font-medium text-emerald-50"
                            >
                              —
                            </p>
                          </template>
                        </div>
                        <div class="mt-3 text-xs text-slate-400">
                          <span v-if="peekSelfGradeExtra.cefr" class="mr-3">CEFR: {{ peekSelfGradeExtra.cefr }}</span>
                          <span v-if="peekSelfGradeExtra.approx" class="mr-3">≈ {{ peekSelfGradeExtra.approx }}</span>
                          <span v-if="peekSelfGradeExtra.phrases.length">Phrases: {{ peekSelfGradeExtra.phrases.slice(0,3).join(', ') }}</span>
                        </div>
                        <div
                          class="flex flex-wrap items-start justify-between gap-3"
                        >
                          <div class="flex flex-wrap items-center gap-2">
                            <span
                              v-if="question.card_type"
                              class="rounded-full bg-slate-800 px-2 py-1 text-[11px] uppercase tracking-wide text-slate-400"
                            >
                              {{ question.card_type }}
                            </span>
                            <span
                              v-if="
                                question.card_type === 'vocab' &&
                                question.part_of_speech
                              "
                              class="rounded-full bg-slate-800 px-2 py-1 text-[11px] uppercase tracking-wide text-slate-400"
                            >
                              {{
                                partOfSpeechDisplayLabel(
                                  question.part_of_speech,
                                )
                              }}
                            </span>
                          </div>
                          <div
                            v-if="peekSelfGradePronunciations.length"
                            class="min-w-[10rem]"
                          >
                            <p
                              class="text-xs uppercase tracking-wide text-slate-500"
                            >
                              Pronunciation
                            </p>
                            <div class="space-y-1">
                              <p
                                v-for="line in peekSelfGradePronunciations"
                                :key="line"
                                class="text-sm text-slate-200"
                              >
                                {{ line }}
                              </p>
                            </div>
                          </div>
                        </div>

                        <div v-if="peekSelfGradeMedia.length" class="mt-4">
                          <p
                            class="text-xs uppercase tracking-wide text-slate-500"
                          >
                            Media
                          </p>
                          <div class="mt-2 flex flex-wrap gap-2">
                            <a
                              v-for="(url, index) in peekSelfGradeMedia"
                              :key="index"
                              :href="url"
                              target="_blank"
                              rel="noopener noreferrer"
                              class="rounded bg-slate-800 px-2 py-1 text-xs text-slate-300 hover:bg-slate-700"
                            >
                              {{ url }}
                            </a>
                          </div>
                        </div>

                        <div class="mt-4 space-y-4">
                          <div v-if="peekSelfGradeNoteDisplay">
                            <p
                              class="text-xs uppercase tracking-wide text-slate-500"
                            >
                              Note
                            </p>
                            <div
                              class="mt-1 prose prose-invert prose-sm prose-p:my-1 prose-li:my-0.5 text-slate-300"
                              v-html="peekSelfGradeNoteDisplay"
                            ></div>
                          </div>

                          <div v-if="peekSelfGradeExampleDisplay">
                            <p
                              class="text-xs uppercase tracking-wide text-slate-500"
                            >
                              Example
                            </p>
                            <div
                              class="mt-1 prose prose-invert prose-sm prose-p:my-1 prose-li:my-0.5 text-slate-300"
                              v-html="peekSelfGradeExampleDisplay"
                            ></div>
                          </div>
                        </div>
                      </div>
                      <div
                        v-if="!isSelfGradeSession && revealedNoteDisplay"
                        class="mt-4 text-left text-sm leading-relaxed text-slate-400"
                      >
                        <span
                          class="text-xs font-medium uppercase tracking-wide text-slate-500"
                          >Note</span
                        >
                        <div
                          class="mt-1 block max-w-full prose prose-invert prose-sm prose-p:my-1 prose-li:my-0.5 text-slate-300"
                          v-html="revealedNoteDisplay"
                        />
                      </div>
                      <div
                        v-if="!isSelfGradeSession && revealedExampleDisplay"
                        class="mt-3 text-left text-sm leading-relaxed text-slate-400"
                      >
                        <span
                          class="text-xs font-medium uppercase tracking-wide text-slate-500"
                          >Example</span
                        >
                        <div
                          class="mt-1 block max-w-full prose prose-invert prose-sm prose-p:my-1 prose-li:my-0.5 text-slate-300"
                          v-html="revealedExampleDisplay"
                        />
                      </div>
                      <div class="mt-3 text-xs text-slate-400">
                        <span v-if="revealedExtra.cefr" class="mr-3">CEFR: {{ revealedExtra.cefr }}</span>
                        <span v-if="revealedExtra.approx" class="mr-3">≈ {{ revealedExtra.approx }}</span>
                        <span v-if="revealedExtra.phrases.length">Phrases: {{ revealedExtra.phrases.slice(0,3).join(', ') }}</span>
                      </div>
                      <p
                        v-if="canFlipCard || isSelfGradeSession"
                        class="mt-4 text-xs text-slate-500"
                      >
                        Tap card to return to prompt
                      </p>
                    </div>
                  </div>
                </button>
              </div>
              <template #fallback>
                <div
                  class="rounded-xl border border-slate-700 bg-slate-900 p-8 pt-12 text-center text-lg text-white"
                >
                  {{ questionFront }}
                </div>
              </template>
            </ClientOnly>
          </div>

          <div
            v-if="progressVisible && !isSelfGradeSession"
            class="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-800"
            aria-hidden="true"
          >
            <div
              :key="progressBarKey"
              class="session-progress-bar h-full w-full origin-left rounded-full bg-emerald-500"
            />
          </div>

          <div v-if="isSelfGradeSession" class="mt-6 space-y-3">
            <p class="text-xs text-slate-500">
              How well do you remember this card?
            </p>
            <div class="grid max-w-lg gap-2 sm:grid-cols-3">
              <button
                type="button"
                class="rounded-lg border border-emerald-800/60 bg-emerald-950/40 px-3 py-3 text-sm font-medium text-emerald-100 hover:bg-emerald-900/50 disabled:opacity-50"
                :disabled="selfGradeSubmitting"
                @click="submitSelfGrade('known')"
              >
                Know well
              </button>
              <button
                type="button"
                class="rounded-lg border border-amber-800/50 bg-amber-950/30 px-3 py-3 text-sm font-medium text-amber-100/90 hover:bg-amber-900/40 disabled:opacity-50"
                :disabled="selfGradeSubmitting"
                @click="submitSelfGrade('unsure')"
              >
                Unsure
              </button>
              <button
                type="button"
                class="rounded-lg border border-red-900/50 bg-red-950/30 px-3 py-3 text-sm font-medium text-red-200/90 hover:bg-red-900/40 disabled:opacity-50"
                :disabled="selfGradeSubmitting"
                @click="submitSelfGrade('forgot')"
              >
                Forgot
              </button>
            </div>
          </div>
          <div v-else class="mt-6 space-y-3">
            <input
              v-model="answer"
              type="text"
              class="w-full max-w-md rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500 disabled:opacity-60"
              placeholder="Your answer"
              :disabled="inputLocked"
              @keyup.enter="onEnterAnswer"
            />
            <div class="flex flex-wrap items-center justify-between gap-2">
              <div class="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  class="inline-flex min-w-[5.5rem] items-center justify-center rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
                  :disabled="submitLoading || gradedRoundActive"
                  @click="submit"
                >
                  {{ submitLoading ? "…" : "Submit" }}
                </button>
                <button
                  type="button"
                  class="inline-flex items-center gap-1.5 rounded-lg border border-slate-600 px-3 py-2 text-sm text-slate-200 hover:bg-slate-800 disabled:opacity-50"
                  :disabled="hintLoading || gradedRoundActive"
                  @click="fetchHint"
                >
                  <Lightbulb
                    class="h-4 w-4 text-amber-400"
                    aria-hidden="true"
                  />
                  {{ hintLoading ? "Hint…" : "Hint" }}
                </button>
                <button
                  v-if="gradedRoundActive && !resultOk"
                  type="button"
                  class="inline-flex items-center gap-1.5 rounded-lg border border-slate-600 px-3 py-2 text-sm text-slate-200 hover:bg-slate-800 disabled:opacity-50"
                  :disabled="explainLoading"
                  @click="fetchExplain"
                >
                  {{ explainLoading ? "Explain…" : "Explain (AI)" }}
                </button>
              </div>
              <button
                type="button"
                class="inline-flex items-center gap-1 rounded-lg border border-slate-600 px-4 py-2 text-sm text-slate-200 hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
                :disabled="!canClickNext || submitLoading"
                @click="doAdvance"
              >
                Next
                <ChevronRight class="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
            <div
              v-if="hintPanelOpen && (hintText || hintError)"
              class="rounded-lg border border-amber-900/40 bg-amber-950/20 px-3 py-2 text-sm text-amber-100/90"
            >
              <div class="flex items-start justify-between gap-2">
                <p class="flex-1">{{ hintError || hintText }}</p>
                <button
                  type="button"
                  class="shrink-0 text-xs text-slate-400 hover:text-white"
                  @click="hintPanelOpen = false"
                >
                  Hide
                </button>
              </div>
            </div>
            <p
              v-if="resultLabel"
              class="text-sm"
              :class="resultOk ? 'text-emerald-400' : 'text-red-400'"
            >
              {{ resultLabel }}
            </p>
            <p v-if="resultNote" class="text-xs text-slate-500">
              {{ resultNote }}
            </p>
            <div
              v-if="
                gradedRoundActive && !resultOk && (explainText || explainError)
              "
              class="rounded-lg border border-slate-700 bg-slate-900/50 px-3 py-2 text-sm text-slate-300"
            >
              <p class="text-xs font-medium text-slate-500">AI explanation</p>
              <p class="mt-1 whitespace-pre-wrap">
                {{ explainError || explainText }}
              </p>
            </div>
          </div>
        </div>

        <div
          v-else
          class="rounded-xl border border-slate-800 bg-slate-900/50 p-8"
        >
          <template v-if="finishPending">
            <p class="text-center text-lg text-slate-200">Queue finished</p>
            <p class="mt-2 text-center text-sm text-slate-500">
              Loading summary…
            </p>
            <div
              class="mx-auto mt-6 h-9 w-9 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent"
              aria-hidden="true"
            />
          </template>
          <template v-else>
            <p class="text-center text-lg text-slate-200">Queue finished</p>
            <p v-if="finishError" class="mt-2 text-center text-sm text-red-400">
              {{ finishError }}
            </p>
            <template
              v-else-if="summary && sessionInteractionMode === 'self_grade'"
            >
              <template v-if="selfGradeFinishStats">
                <p class="mt-2 text-center text-sm text-slate-300">
                  Self-grade · {{ selfGradeFinishStats.cards }}
                  {{
                    selfGradeFinishStats.cards === 1 ? "card" : "cards"
                  }}
                  (last rating each)
                </p>
                <dl
                  class="mx-auto mt-4 grid max-w-sm grid-cols-3 gap-2 text-center text-xs text-slate-400 sm:text-sm"
                >
                  <div
                    class="rounded-lg border border-slate-800 bg-slate-950/50 px-2 py-2"
                  >
                    <dt
                      class="text-[10px] uppercase tracking-wide text-slate-500"
                    >
                      Know well
                    </dt>
                    <dd class="mt-1 text-lg font-semibold text-emerald-300/90">
                      {{ selfGradeFinishStats.known }}
                    </dd>
                  </div>
                  <div
                    class="rounded-lg border border-slate-800 bg-slate-950/50 px-2 py-2"
                  >
                    <dt
                      class="text-[10px] uppercase tracking-wide text-slate-500"
                    >
                      Unsure
                    </dt>
                    <dd class="mt-1 text-lg font-semibold text-amber-200/90">
                      {{ selfGradeFinishStats.unsure }}
                    </dd>
                  </div>
                  <div
                    class="rounded-lg border border-slate-800 bg-slate-950/50 px-2 py-2"
                  >
                    <dt
                      class="text-[10px] uppercase tracking-wide text-slate-500"
                    >
                      Forgot
                    </dt>
                    <dd class="mt-1 text-lg font-semibold text-red-300/90">
                      {{ selfGradeFinishStats.forgot }}
                    </dd>
                  </div>
                </dl>
                <p
                  class="mt-3 text-center text-xs leading-relaxed text-slate-500"
                >
                  Summary and list use your final choice per card in this
                  session (intermediate rounds are not listed twice).
                </p>
              </template>
              <p v-else class="mt-2 text-center text-sm text-slate-400">
                Self-grade (summary breakdown unavailable)
              </p>
            </template>
            <p
              v-else-if="summary"
              class="mt-2 text-center text-sm text-slate-400"
            >
              {{ summary.correct }} / {{ summary.questions }} correct ({{
                Math.round((summary.accuracy || 0) * 100)
              }}%)
            </p>
            <ul
              v-if="reviewItems.length"
              class="mt-6 max-h-80 space-y-2 overflow-y-auto text-left text-sm"
            >
              <li
                v-for="(row, idx) in reviewItems"
                :key="`${row.card_id}-${idx}`"
                class="rounded-lg border border-slate-800 bg-slate-950/40 px-3 py-2"
              >
                <div class="flex flex-wrap items-start justify-between gap-2">
                  <div class="min-w-0 flex-1 text-slate-200">
                    <span class="font-medium text-slate-100">{{
                      row.front?.content ?? "—"
                    }}</span>
                    <span class="mx-1 text-slate-600">→</span>
                    <span class="text-slate-400">{{
                      backSummaryPreview(row.back?.content)
                    }}</span>
                  </div>
                  <span
                    class="shrink-0 rounded px-2 py-0.5 text-xs font-medium"
                    :class="
                      row.grading_mode === 'self_grade'
                        ? row.self_rating === 'known'
                          ? 'bg-emerald-950/60 text-emerald-200'
                          : row.self_rating === 'unsure'
                            ? 'bg-amber-950/50 text-amber-100/90'
                            : row.self_rating === 'forgot'
                              ? 'bg-red-950/50 text-red-200/90'
                              : 'bg-slate-800 text-slate-200'
                        : row.result === 'correct'
                          ? 'bg-emerald-900/50 text-emerald-300'
                          : 'bg-red-900/40 text-red-300'
                    "
                  >
                    {{
                      row.grading_mode === "self_grade"
                        ? selfRatingLabel(row.self_rating)
                        : row.result === "correct"
                          ? "Correct"
                          : "Wrong"
                    }}
                  </span>
                </div>
                <p v-if="row.response" class="mt-1 text-xs text-slate-500">
                  You: <span class="text-slate-400">{{ row.response }}</span>
                  <span v-if="row.match_type" class="text-slate-600">
                    · {{ row.match_type }}</span
                  >
                </p>
              </li>
            </ul>
            <div class="mt-6 text-center">
              <button
                type="button"
                class="rounded-lg border border-slate-600 px-4 py-2 text-sm text-slate-200 hover:bg-slate-800"
                @click="resetSession"
              >
                New session
              </button>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ChevronRight, Lightbulb, Volume2 } from "lucide-vue-next";
import { PART_OF_SPEECH_OPTIONS } from "~/constants/partOfSpeech";
import { htmlToPlainText, isEmptyRichText } from "~/utils/richText";
import { sanitizeRichHtml } from "~/utils/sanitizeRichHtml";

definePageMeta({
  layout: "default",
  middleware: "auth",
});

const AUTO_KEY = "vocko-learning-auto-advance";
const AUTO_AUDIO_KEY = "vocko-learning-auto-audio";

const route = useRoute();
const { api } = useApi();

type TypoHighlight = {
  start: number;
  end: number;
  kind: "substitute" | "insert" | "delete";
};

type Q = {
  card_id: string;
  front?: { content?: string };
  back?: { content?: string };
  question_type?: string;
  has_stored_hint?: boolean;
  card_type?: string;
  part_of_speech?: string;
  language?: string;
  note?: string;
  example?: string;
  media?: string[];
  pronunciation_us?: string;
  pronunciation_uk?: string;
};

type ReviewItem = {
  card_id: string;
  front?: { content?: string };
  back?: { content?: string };
  result?: string;
  response?: string;
  match_type?: string;
  note?: string;
  typo_highlight?: TypoHighlight;
  self_rating?: string;
  grading_mode?: string;
};

type AnswerApi = {
  result: string;
  match_type?: string;
  note?: string;
  typo_highlight?: TypoHighlight;
  session_answered?: number;
  session_correct?: number;
  card_back?: { content?: string };
  flashcard_note?: string;
  flashcard_example?: string;
};

type SelfGradeApi = AnswerApi & {
  round_complete?: boolean;
  pending_round_choice?: boolean;
  breakdown?: { known: number; unsure: number; forgot: number };
  round_index?: number;
};

type QueueMeta = {
  strategy?: string;
  mode?: string;
  counts?: Record<string, number>;
  note?: string;
};

const deckId = computed(() => (route.query.deck_id as string) || "");
/** True only after successful GET /decks/:id with card_count === 0. On fetch error, stays false so Start is allowed. */
const deckEmptyBlocked = ref(false);
/** Set from start session API; '' before first session this page visit. */
const sessionInteractionMode = ref<"typed" | "self_grade" | "">("");
const isSelfGradeSession = computed(
  () =>
    sessionInteractionMode.value === "self_grade" ||
    (!sessionId.value && route.query.interaction === "self_grade"),
);
const selfRoundBreak = ref<{
  breakdown: { known: number; unsure: number; forgot: number };
  roundIndex: number;
} | null>(null);
const continueRoundLoading = ref(false);
const continueRoundError = ref("");
const selfGradeSubmitting = ref(false);
/** Cards in the current self-grade round (from queue_meta.total or continue-round queue_length). */
const selfGradeRoundTotal = ref(0);
/** Ratings submitted this round (resets when a new round starts). */
const selfGradeCompletedInRound = ref(0);

const mode = ref<"learn" | "review">("learn");
const smartQueue = ref(true);
const sessionId = ref("");
const queueMeta = ref<QueueMeta | null>(null);
const question = ref<Q | null>(null);
const answer = ref("");
const resultLabel = ref("");
const resultOk = ref(false);
const sessionError = ref("");
type SelfGradeSessionSummary = {
  /** Unique cards, each counted once with the last rating in this session. */
  cards: number;
  known: number;
  unsure: number;
  forgot: number;
  /** Legacy API: total rating events (undeduplicated). */
  attempts?: number;
};

type SessionFinishSummary = {
  questions: number;
  correct: number;
  accuracy: number;
  self_grade?: SelfGradeSessionSummary;
};

const summary = ref<SessionFinishSummary | null>(null);
const reviewItems = ref<ReviewItem[]>([]);
const finishPending = ref(false);
const finishError = ref("");

const hintText = ref("");
const hintError = ref("");
const hintLoading = ref(false);
const hintPanelOpen = ref(false);
const resultNote = ref("");

const autoAdvance = ref(true);
/** Auto-read front on new question (vocab + English); default off */
const autoAudio = ref(false);
const submitLoading = ref(false);
const gradedRoundActive = ref(false);
const canClickNext = ref(false);
const progressVisible = ref(false);
const progressBarKey = ref(0);
const cardFlipped = ref(false);
const revealedBack = ref<{ content?: string } | null>(null);
const revealedNote = ref("");
const revealedExample = ref("");

const revealedBackDisplay = computed(() => {
  const raw = revealedBack.value?.content;
  if (isEmptyRichText(raw)) return "";
  return sanitizeRichHtml(raw);
});

const revealedExtra = computed(() => {
  return {
    cefr: (question.value && question.value.cefr) || '',
    approx: (question.value && question.value.approx) || '',
    phrases: Array.isArray(question.value?.phrases) ? question.value?.phrases : [],
  }
})

const revealedNoteDisplay = computed(() => {
  if (isEmptyRichText(revealedNote.value)) return "";
  return sanitizeRichHtml(revealedNote.value);
});

const revealedExampleDisplay = computed(() => {
  if (isEmptyRichText(revealedExample.value)) return "";
  return sanitizeRichHtml(revealedExample.value);
});

function backSummaryPreview(content: string | undefined) {
  const t = htmlToPlainText(content);
  return t || "—";
}
const sessionAnswered = ref(0);
const sessionCorrect = ref(0);

const selfGradeProgressPct = computed(() => {
  const t = selfGradeRoundTotal.value;
  if (t <= 0) return 0;
  return Math.min(100, (selfGradeCompletedInRound.value / t) * 100);
});

const explainText = ref("");
const explainError = ref("");
const explainLoading = ref(false);

let advanceTimerId: ReturnType<typeof setTimeout> | null = null;

const smartQueueTitle = computed(() => {
  if (!smartQueue.value) {
    return mode.value === "review"
      ? "Classic review: due cards, oldest due first"
      : "Classic learn: new (shuffled) then due, then fill";
  }
  return mode.value === "review"
    ? "Smart review: prioritize weak tags / hard due cards"
    : "Smart learn: ~70% weak-priority · 20% new · 10% easy";
});

const queueMetaLine = computed(() => {
  const m = queueMeta.value;
  if (!m?.counts) return "";
  const c = m.counts;
  if (m.strategy === "self_grade") {
    return `Self-grade: ${c.total ?? 0} cards (full deck, shuffled).`;
  }
  const parts: string[] = [];
  if (m.strategy === "smart" && m.mode === "learn") {
    parts.push(
      `${c.weak ?? 0} weak-priority`,
      `${c.new ?? 0} new`,
      `${c.easy ?? 0} easy`,
    );
    if ((c.fill ?? 0) > 0) parts.push(`${c.fill} fill`);
  } else if (m.strategy === "smart" && m.mode === "review") {
    parts.push(`${c.due ?? c.total ?? 0} due`);
    if ((c.priority_high ?? 0) > 0)
      parts.push(`${c.priority_high} high-priority`);
  } else {
    if ((c.new ?? 0) > 0) parts.push(`${c.new} new`);
    if ((c.due ?? 0) > 0) parts.push(`${c.due} due`);
    if ((c.fill ?? 0) > 0) parts.push(`${c.fill} fill`);
    if (parts.length === 0) parts.push("composition n/a");
  }
  const total = c.total ?? "?";
  return `Queue (${m.strategy}, ${m.mode}): ${parts.join(" · ")} · total ${total}.`;
});

const questionFront = computed(() => question.value?.front?.content ?? "—");

const peekSelfGradeBackHtml = computed(() => {
  const raw = question.value?.back?.content;
  if (isEmptyRichText(raw)) return "";
  return sanitizeRichHtml(raw || "");
});

const peekSelfGradeExtra = computed(() => {
  return {
    cefr: question.value?.cefr ?? '',
    approx: question.value?.approx ?? '',
    phrases: Array.isArray(question.value?.phrases) ? question.value?.phrases : [],
  }
})

const peekSelfGradeNoteDisplay = computed(() => {
  const raw = question.value?.note;
  if (isEmptyRichText(raw)) return "";
  return sanitizeRichHtml(raw || "");
});

const peekSelfGradeExampleDisplay = computed(() => {
  const raw = question.value?.example;
  if (isEmptyRichText(raw)) return "";
  return sanitizeRichHtml(raw || "");
});

const peekSelfGradePronunciations = computed(() => {
  const us = question.value?.pronunciation_us?.trim();
  const uk = question.value?.pronunciation_uk?.trim();
  const lines: string[] = [];
  if (us) lines.push(`US: ${us}`);
  if (uk) lines.push(`UK: ${uk}`);
  return lines;
});

const peekSelfGradeMedia = computed(() => {
  const raw = question.value?.media;
  if (!raw) return [];
  if (Array.isArray(raw))
    return raw.filter((item): item is string => Boolean(item));
  if (typeof raw === "string") return [raw];
  return [];
});

function partOfSpeechDisplayLabel(value: string | undefined) {
  if (!value) return "";
  return PART_OF_SPEECH_OPTIONS.find((o) => o.value === value)?.label ?? value;
}

function frontSpeechEligible(q: Q | null): q is Q {
  if (!q) return false;
  if ((q.card_type ?? "vocab").toLowerCase() !== "vocab") return false;
  const lang = (q.language ?? "en").toLowerCase();
  if (!lang.startsWith("en")) return false;
  return Boolean((q.front?.content ?? "").trim());
}

const frontSpeechAvailable = computed(
  () => !!sessionId.value && frontSpeechEligible(question.value),
);

/**
 * Speaks prompt front verbatim. Browser SpeechSynthesis has no POS/stress hint API:
 * for homographs like "address" (noun vs verb stress), the engine picks one reading from
 * the string alone. True noun/verb disambiguation would need IPA, SSML-capable TTS, etc.
 */
function playFrontSpeech(q: Q | null) {
  if (!import.meta.client) return;
  if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
  if (!frontSpeechEligible(q)) return;
  const text = (q.front?.content ?? "").trim();
  if (!text) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = "en-US";
  window.speechSynthesis.speak(u);
}

const canFlipCard = computed(() => {
  if (sessionInteractionMode.value === "self_grade") {
    return !!question.value && !selfRoundBreak.value;
  }
  return gradedRoundActive.value && revealedBack.value != null;
});

const inputLocked = computed(
  () =>
    submitLoading.value || gradedRoundActive.value || selfGradeSubmitting.value,
);

function cancelAdvanceTimer() {
  if (advanceTimerId !== null) {
    clearTimeout(advanceTimerId);
    advanceTimerId = null;
  }
}

function clearGradeUi() {
  gradedRoundActive.value = false;
  resultLabel.value = "";
  resultNote.value = "";
  resultOk.value = false;
  canClickNext.value = false;
  progressVisible.value = false;
  cardFlipped.value = false;
  revealedBack.value = null;
  revealedNote.value = "";
  revealedExample.value = "";
  explainText.value = "";
  explainError.value = "";
}

function toggleCardFlip() {
  if (!canFlipCard.value) return;
  cardFlipped.value = !cardFlipped.value;
}

function selfRatingLabel(r: string | undefined) {
  if (r === "known") return "Know well";
  if (r === "unsure") return "Unsure";
  if (r === "forgot") return "Forgot";
  return r || "";
}

/** Finish-screen stats for self-grade (from API summary or derived from review items, last rating per card). */
const selfGradeFinishStats = computed((): SelfGradeSessionSummary | null => {
  if (sessionInteractionMode.value !== "self_grade" || !summary.value)
    return null;
  const sg = summary.value.self_grade;
  if (sg != null && typeof sg.cards === "number") {
    return {
      cards: sg.cards,
      known: sg.known ?? 0,
      unsure: sg.unsure ?? 0,
      forgot: sg.forgot ?? 0,
    };
  }
  const items = reviewItems.value;
  if (!items.length) return null;
  const lastById = new Map<string, ReviewItem>();
  for (const row of items) {
    if (row.grading_mode === "self_grade" && row.card_id) {
      lastById.set(row.card_id, row);
    }
  }
  let known = 0;
  let unsure = 0;
  let forgot = 0;
  for (const row of lastById.values()) {
    if (row.self_rating === "known") known++;
    else if (row.self_rating === "unsure") unsure++;
    else if (row.self_rating === "forgot") forgot++;
  }
  const cards = lastById.size;
  if (cards === 0) return null;
  return { cards, known, unsure, forgot };
});

function clearHintForCard() {
  hintText.value = "";
  hintError.value = "";
  hintPanelOpen.value = false;
}

onMounted(() => {
  if (import.meta.client) {
    const v = localStorage.getItem(AUTO_KEY);
    if (v === "0") autoAdvance.value = false;
    if (v === "1") autoAdvance.value = true;
    const aa = localStorage.getItem(AUTO_AUDIO_KEY);
    if (aa === "1") autoAudio.value = true;
    if (aa === "0") autoAudio.value = false;
  }
});

watch(autoAdvance, (on) => {
  if (import.meta.client) localStorage.setItem(AUTO_KEY, on ? "1" : "0");
});

watch(autoAudio, (on) => {
  if (import.meta.client) localStorage.setItem(AUTO_AUDIO_KEY, on ? "1" : "0");
});

watch(
  question,
  (q) => {
    if (!import.meta.client) return;
    if (!q) {
      if (typeof window !== "undefined" && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
      return;
    }
    if (!sessionId.value || !autoAudio.value) return;
    playFrontSpeech(q);
  },
  { flush: "post" },
);

onUnmounted(() => {
  cancelAdvanceTimer();
  if (
    import.meta.client &&
    typeof window !== "undefined" &&
    "speechSynthesis" in window
  ) {
    window.speechSynthesis.cancel();
  }
});

function apiErrorDetail(err: unknown): string | null {
  if (!err || typeof err !== "object") return null;
  const o = err as Record<string, unknown>;
  const data = o.data as Record<string, unknown> | undefined;
  const detail = data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const row = detail[0] as { msg?: string } | undefined;
    if (row?.msg) return row.msg;
  }
  return null;
}

async function refreshDeckEmptyGate() {
  deckEmptyBlocked.value = false;
  const id = deckId.value;
  if (!id) return;
  try {
    const data = await api<{ deck: { card_count?: number } }>(`/decks/${id}`);
    const c = Number(data.deck?.card_count ?? 0);
    deckEmptyBlocked.value = c === 0;
  } catch {
    deckEmptyBlocked.value = false;
  }
}

watch(deckId, refreshDeckEmptyGate, { immediate: true });

async function startSession() {
  if (deckEmptyBlocked.value) return;
  sessionError.value = "";
  summary.value = null;
  reviewItems.value = [];
  finishPending.value = false;
  finishError.value = "";
  answer.value = "";
  queueMeta.value = null;
  selfRoundBreak.value = null;
  continueRoundError.value = "";
  sessionInteractionMode.value = "";
  clearGradeUi();
  cancelAdvanceTimer();
  sessionAnswered.value = 0;
  sessionCorrect.value = 0;
  selfGradeRoundTotal.value = 0;
  selfGradeCompletedInRound.value = 0;
  const selfFromRoute = route.query.interaction === "self_grade";
  try {
    const data = await api<{
      session_id: string;
      preloaded_questions: Q[];
      queue_meta?: QueueMeta;
      interaction_mode?: string;
    }>("/learning/sessions", {
      method: "POST",
      body: {
        deck_id: deckId.value,
        mode: selfFromRoute ? "learn" : mode.value,
        options: selfFromRoute
          ? { interaction_mode: "self_grade", full_deck: true }
          : { queue_size: 30, smart_queue: smartQueue.value },
      },
    });
    sessionId.value = data.session_id;
    queueMeta.value = data.queue_meta ?? null;
    sessionInteractionMode.value =
      data.interaction_mode === "self_grade" ? "self_grade" : "typed";
    if (data.interaction_mode === "self_grade") {
      const total = Number(data.queue_meta?.counts?.total ?? 0);
      selfGradeRoundTotal.value = total;
      selfGradeCompletedInRound.value = 0;
    }
    const first = data.preloaded_questions?.[0];
    question.value = first || null;
    clearHintForCard();
    if (!first) {
      sessionError.value =
        "No cards in queue for this mode. Try Learn or add cards.";
      sessionId.value = "";
      queueMeta.value = null;
      sessionInteractionMode.value = "";
      selfGradeRoundTotal.value = 0;
      selfGradeCompletedInRound.value = 0;
    }
  } catch (e: unknown) {
    sessionError.value = apiErrorDetail(e) ?? "Could not start session";
    sessionInteractionMode.value = "";
  }
}

async function getNext() {
  cancelAdvanceTimer();
  clearGradeUi();
  const data = await api<{
    question: Q | null;
    interaction_mode?: string;
    pending_round_choice?: boolean;
    breakdown?: { known: number; unsure: number; forgot: number };
    round_index?: number;
  }>(`/learning/sessions/${sessionId.value}/next`);
  if (data.interaction_mode === "self_grade") {
    sessionInteractionMode.value = "self_grade";
  }
  if (data.pending_round_choice && data.breakdown) {
    selfRoundBreak.value = {
      breakdown: data.breakdown,
      roundIndex: data.round_index ?? 0,
    };
    question.value = null;
    answer.value = "";
    clearHintForCard();
    return;
  }
  selfRoundBreak.value = null;
  question.value = data.question;
  answer.value = "";
  clearHintForCard();
  if (!data.question) {
    finishPending.value = true;
    finishError.value = "";
    try {
      await finish();
    } finally {
      finishPending.value = false;
    }
  }
}

async function fetchExplain() {
  if (!question.value || !deckId.value) return;
  explainLoading.value = true;
  explainError.value = "";
  explainText.value = "";
  try {
    const data = await api<{ explanation: string }>("/learning/explain", {
      method: "POST",
      body: { card_id: question.value.card_id, deck_id: deckId.value },
    });
    explainText.value = data.explanation;
  } catch (e: unknown) {
    const fe = e as { data?: { detail?: string | { msg?: string }[] } };
    const d = fe.data?.detail;
    if (typeof d === "string") {
      explainError.value =
        d.includes("OPENROUTER") || d.includes("503")
          ? "AI explain needs the server API key configured. Ask your admin or try again later."
          : d;
    } else if (Array.isArray(d)) {
      explainError.value =
        d
          .map((x) => x.msg ?? "")
          .filter(Boolean)
          .join(" ") || "Could not load explanation";
    } else {
      explainError.value = "Could not load explanation";
    }
  } finally {
    explainLoading.value = false;
  }
}

async function fetchHint() {
  if (!sessionId.value || !question.value || gradedRoundActive.value) return;
  hintLoading.value = true;
  hintError.value = "";
  hintPanelOpen.value = true;
  try {
    const data = await api<{ hint: string; source: string }>(
      `/learning/sessions/${sessionId.value}/hint`,
      {
        method: "POST",
        body: { card_id: question.value.card_id },
      },
    );
    hintText.value = data.hint;
  } catch (e: unknown) {
    const fe = e as { data?: { detail?: string | { msg?: string }[] } };
    const d = fe.data?.detail;
    hintText.value = "";
    if (typeof d === "string") hintError.value = d;
    else if (Array.isArray(d))
      hintError.value =
        d
          .map((x) => x.msg ?? "")
          .filter(Boolean)
          .join(" ") || "Could not load hint";
    else hintError.value = "Could not load hint";
  } finally {
    hintLoading.value = false;
  }
}

function scheduleAdvanceAfterGrade() {
  cancelAdvanceTimer();
  gradedRoundActive.value = true;
  canClickNext.value = false;
  cardFlipped.value = false;
  if (autoAdvance.value) {
    progressVisible.value = true;
    progressBarKey.value += 1;
    advanceTimerId = setTimeout(() => {
      advanceTimerId = null;
      void doAdvance();
    }, 2000);
  } else {
    progressVisible.value = false;
    canClickNext.value = true;
  }
}

async function doAdvance() {
  cancelAdvanceTimer();
  clearGradeUi();
  await getNext();
}

function onEnterAnswer() {
  if (!gradedRoundActive.value && !submitLoading.value) void submit();
}

async function submit() {
  if (!question.value || submitLoading.value || gradedRoundActive.value) return;
  submitLoading.value = true;
  try {
    const data = await api<AnswerApi>(
      `/learning/sessions/${sessionId.value}/answer`,
      {
        method: "POST",
        body: { card_id: question.value.card_id, response: answer.value },
      },
    );
    resultOk.value = data.result === "correct";
    if (data.result === "correct") {
      const mt = data.match_type;
      if (mt === "synonym" || mt === "llm")
        resultLabel.value = "Correct (close match)";
      else if (mt === "typo" || mt === "typo_one")
        resultLabel.value = "Correct (one typo)";
      else resultLabel.value = "Correct";
    } else {
      resultLabel.value = "Incorrect";
    }
    const parts: string[] = [];
    const mtOk = data.match_type;
    if ((mtOk === "synonym" || mtOk === "llm") && data.result === "correct")
      parts.push("Graded with AI");
    if (data.note) parts.push(data.note);
    resultNote.value = parts.join(" · ");

    if (typeof data.session_answered === "number")
      sessionAnswered.value = data.session_answered;
    if (typeof data.session_correct === "number")
      sessionCorrect.value = data.session_correct;

    revealedBack.value = data.card_back ?? { content: undefined };
    revealedNote.value = data.flashcard_note ?? "";
    revealedExample.value = data.flashcard_example ?? "";

    scheduleAdvanceAfterGrade();
  } catch {
    resultLabel.value = "Submit failed";
    resultOk.value = false;
    resultNote.value = "";
  } finally {
    submitLoading.value = false;
  }
}

async function finish() {
  if (!sessionId.value) return;
  try {
    const data = await api<{
      summary: SessionFinishSummary;
      items?: ReviewItem[];
      interaction_mode?: string;
    }>(`/learning/sessions/${sessionId.value}/finish`, { method: "POST" });
    summary.value = data.summary;
    reviewItems.value = data.items ?? [];
    finishError.value = "";
    if (data.interaction_mode === "self_grade") {
      sessionInteractionMode.value = "self_grade";
    }
  } catch {
    summary.value = null;
    reviewItems.value = [];
    finishError.value = "Could not load session summary.";
  }
  question.value = null;
  selfRoundBreak.value = null;
}

async function finishSelfGradeSession() {
  continueRoundError.value = "";
  finishPending.value = true;
  try {
    await finish();
  } finally {
    finishPending.value = false;
  }
}

async function continueSelfRound(scope: "weak" | "all") {
  if (!sessionId.value) return;
  continueRoundError.value = "";
  continueRoundLoading.value = true;
  try {
    const cont = await api<{ queue_length?: number }>(
      `/learning/sessions/${sessionId.value}/continue-round`,
      {
        method: "POST",
        body: { scope },
      },
    );
    const ql = Number(cont.queue_length ?? 0);
    selfGradeRoundTotal.value = ql;
    selfGradeCompletedInRound.value = 0;
    selfRoundBreak.value = null;
    await getNext();
  } catch (e: unknown) {
    continueRoundError.value =
      apiErrorDetail(e) ?? "Could not start next round";
  } finally {
    continueRoundLoading.value = false;
  }
}

async function submitSelfGrade(rating: "known" | "unsure" | "forgot") {
  if (!question.value || selfGradeSubmitting.value || selfRoundBreak.value)
    return;
  selfGradeSubmitting.value = true;
  try {
    const data = await api<SelfGradeApi>(
      `/learning/sessions/${sessionId.value}/self-grade`,
      {
        method: "POST",
        body: { card_id: question.value.card_id, rating },
      },
    );
    if (typeof data.session_answered === "number")
      sessionAnswered.value = data.session_answered;
    if (typeof data.session_correct === "number")
      sessionCorrect.value = data.session_correct;
    selfGradeCompletedInRound.value += 1;
    cardFlipped.value = false;
    if (data.round_complete && data.breakdown) {
      selfRoundBreak.value = {
        breakdown: data.breakdown,
        roundIndex: data.round_index ?? 0,
      };
      question.value = null;
      return;
    }
    await getNext();
  } catch {
    /* keep question; user can retry */
  } finally {
    selfGradeSubmitting.value = false;
  }
}

function resetSession() {
  cancelAdvanceTimer();
  sessionId.value = "";
  queueMeta.value = null;
  question.value = null;
  summary.value = null;
  reviewItems.value = [];
  finishPending.value = false;
  finishError.value = "";
  sessionError.value = "";
  sessionInteractionMode.value = "";
  selfRoundBreak.value = null;
  continueRoundError.value = "";
  clearHintForCard();
  clearGradeUi();
  sessionAnswered.value = 0;
  sessionCorrect.value = 0;
  selfGradeRoundTotal.value = 0;
  selfGradeCompletedInRound.value = 0;
  void refreshDeckEmptyGate();
}
</script>

<style scoped>
@keyframes session-progress-linear {
  from {
    transform: scaleX(0);
  }
  to {
    transform: scaleX(1);
  }
}

.session-progress-bar {
  transform: scaleX(0);
  transform-origin: left center;
  animation: session-progress-linear 2s linear forwards;
  will-change: transform;
}
</style>
