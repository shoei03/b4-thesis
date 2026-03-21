package jp.ac.osaka_u.sdl.nil.usecase.preprocess.python

import PythonLexer
import PythonParser
import PythonParserBaseListener
import jp.ac.osaka_u.sdl.nil.NILConfig
import jp.ac.osaka_u.sdl.nil.entity.Parameter
import jp.ac.osaka_u.sdl.nil.usecase.preprocess.AntlrTransformer
import jp.ac.osaka_u.sdl.nil.usecase.preprocess.MethodInfo
import org.antlr.v4.runtime.Parser
import org.antlr.v4.runtime.ParserRuleContext
import org.antlr.v4.runtime.Token
import org.antlr.v4.runtime.tree.ParseTreeListener

class PythonTransformer(config: NILConfig) :
    AntlrTransformer(
        config,
        ::PythonLexer,
        ::PythonParser
    ) {
    override fun createVisitor(action: (ParserRuleContext) -> Unit): ParseTreeListener =
        object : PythonParserBaseListener() {
            override fun enterFunction_def(ctx: PythonParser.Function_defContext) {
                action(ctx)
            }
        }

    override fun Parser.extractRuleContext(): ParserRuleContext =
        (this as PythonParser).file_input()

    override fun Token.isNegligible(): Boolean =
        this.text.run {
            this.isEmpty() || this[0] == '\n' || this[0] == ' ' || this[0] == '\r' ||
                this[0] == '#'
        }

    override fun extractMethodInfo(ctx: ParserRuleContext): MethodInfo {
        if (ctx !is PythonParser.Function_defContext) {
            return MethodInfo(null, null, null)
        }

        // Get the raw function definition (handles both sync and async functions)
        val rawFuncDef = ctx.function_def_raw() ?: return MethodInfo(null, null, null)

        // Extract raw method name
        val rawMethodName = rawFuncDef.NAME()?.text

        // Extract class name (if inside a class)
        val className = extractClassName(ctx)

        // Combine class name and method name with dot notation
        val fullMethodName = if (className != null && rawMethodName != null) {
            "$className.$rawMethodName"
        } else {
            rawMethodName
        }

        // Extract return type (from '-> expression' part)
        val returnType = rawFuncDef.expression()?.text

        // Extract parameters
        val parameters = rawFuncDef.params()?.parameters()?.let { params ->
            extractParameters(params)
        }

        return MethodInfo(fullMethodName, returnType, parameters)
    }

    /**
     * Extract the fully qualified class name by traversing up the parse tree.
     * For nested classes, returns "OuterClass.InnerClass" format.
     * Returns null for top-level functions.
     */
    private fun extractClassName(ctx: ParserRuleContext): String? {
        val classNames = mutableListOf<String>()
        var parent = ctx.parent

        // Traverse up the parse tree to find all enclosing class definitions
        while (parent != null) {
            if (parent is PythonParser.Class_def_rawContext) {
                // Extract class name and add to the beginning of the list
                parent.NAME()?.text?.let { classNames.add(0, it) }
            }
            parent = parent.parent
        }

        // Return null for top-level functions, otherwise join with dots
        return if (classNames.isEmpty()) null else classNames.joinToString(".")
    }

    private fun extractParameters(params: PythonParser.ParametersContext): List<Parameter> {
        val paramList = mutableListOf<Parameter>()

        // Extract parameters from different parts of the grammar
        // slash_no_default: required positional parameters before /
        params.slash_no_default()?.param_no_default()?.forEach { paramCtx ->
            paramCtx.param()?.let { p ->
                paramList.add(extractParameter(p))
            }
        }

        // slash_with_default: positional parameters with defaults before /
        params.slash_with_default()?.let { slash ->
            slash.param_no_default()?.forEach { paramCtx ->
                paramCtx.param()?.let { p ->
                    paramList.add(extractParameter(p))
                }
            }
            slash.param_with_default()?.forEach { paramCtx ->
                paramCtx.param()?.let { p ->
                    paramList.add(extractParameter(p))
                }
            }
        }

        // param_no_default: regular required parameters
        params.param_no_default()?.forEach { paramCtx ->
            paramCtx.param()?.let { p ->
                paramList.add(extractParameter(p))
            }
        }

        // param_with_default: parameters with default values
        params.param_with_default()?.forEach { paramCtx ->
            paramCtx.param()?.let { p ->
                paramList.add(extractParameter(p))
            }
        }

        // star_etc: *args, **kwargs, and keyword-only parameters
        params.star_etc()?.let { starEtc ->
            // *args parameter
            starEtc.param_no_default()?.param()?.let { p ->
                paramList.add(Parameter("*${p.NAME().text}", p.annotation()?.expression()?.text ?: "Any"))
            }
            
            starEtc.param_no_default_star_annotation()?.param_star_annotation()?.let { p ->
                paramList.add(Parameter("*${p.NAME().text}", p.star_annotation()?.star_expression()?.text ?: "Any"))
            }

            // keyword-only parameters after *
            starEtc.param_maybe_default()?.forEach { paramCtx ->
                paramCtx.param()?.let { p ->
                    paramList.add(extractParameter(p))
                }
            }

            // **kwargs parameter
            starEtc.kwds()?.param_no_default()?.param()?.let { p ->
                paramList.add(Parameter("**${p.NAME().text}", p.annotation()?.expression()?.text ?: "Any"))
            }
        }

        return paramList
    }

    private fun extractParameter(param: PythonParser.ParamContext): Parameter {
        val name = param.NAME()?.text ?: "unknown"
        val type = param.annotation()?.expression()?.text ?: "Any"
        return Parameter(name, type)
    }
}
